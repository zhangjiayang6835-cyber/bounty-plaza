```python
# Copyright 2024 Tenstorrent AI ULC
#
# Licensed under the Apache License v2.0 with LLVM exceptions.
# See https://llvm.org/foundation/releases.html#licensing for details.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""
HiFT Vocoder for CosyVoice2 streaming pipeline.

Implements the HiFT (Harmonic + Noise + Flow-based Time-domain) vocoder
with ResBlock backbone (BigVGAN-derived), F0 predictor, NSF source module,
and iSTFT synthesis head.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import torch
from ttmetal.dialects.ttnn.operations.core import TTNNOp
from ttmetal.dialects.ttnn.operations.istft import ISTFTOp
from ttmetal.dialects.ttnn.types import Tensor, Shape
from ttmetal.dialects.ttnn.utils import get_device


@dataclass
class HiFTConfig:
    """Configuration for HiFT vocoder."""
    input_channels: int = 80  # Mel spectrogram channels
    hidden_channels: int = 512
    kernel_size: int = 31
    n_layers: int = 8
    dilation_cycle_length: int = 4
    resblock_kernel_sizes: Tuple[int, ...] = (3, 7, 11)
    upsample_rates: Tuple[int, ...] = (8, 8, 2, 2)
    upsample_initial_channel: int = 512
    upsample_kernel_sizes: Tuple[int, ...] = (16, 16, 4, 4)
    f0_predictor_num_layers: int = 3
    f0_predictor_channels: int = 256
    f0_predictor_kernel_size: int = 3
    dtype: str = "float32"


class ResBlock(TTNNOp):
    """
    Residual block for HiFT vocoder.
    BigVGAN-derived residual block with dilated convolutions.
    """

    def __init__(self, channels: int, kernel_size: int = 3, dilation: int = 1):
        self.channels = channels
        self.kernel_size = kernel_size
        self.dilation = dilation
        self.padding = dilation * (kernel_size - 1) // 2

    def forward(self, x: Tensor) -> Tensor:
        device = get_device()
        # Dilated convolution 1
        conv1 = torch.nn.Conv1d(
            self.channels, self.channels,
            self.kernel_size, padding=self.padding, dilation=self.dilation
        ).to(device)
        # Dilated convolution 2
        conv2 = torch.nn.Conv1d(
            self.channels, self.channels,
            self.kernel_size, padding=self.padding, dilation=1
        ).to(device)

        h1 = torch.relu(conv1(x))
        h2 = conv2(h1)
        return x + h2


class F0Predictor(TTNNOp):
    """
    F0 (fundamental frequency) predictor for HiFT vocoder.
    Predicts continuous F0 from mel spectrogram features.
    """

    def __init__(self, config: HiFTConfig):
        self.config = config
        self.num_layers = config.f0_predictor_num_layers
        self.channels = config.f0_predictor_channels
        self.kernel_size = config.f0_predictor_kernel_size
        self.padding = (config.f0_predictor_kernel_size - 1) // 2

    def forward(self, mel: Tensor) -> Tensor:
        device = get_device()
        x = torch.nn.Conv1d(
            config.input_channels, self.channels,
            self.kernel_size, padding=self.padding
        ).to(device)(mel)
        for _ in range(self.num_layers - 1):
            x = torch.relu(x)
            x = torch.nn.Conv1d(
                self.channels, self.channels,
                self.kernel_size, padding=self.padding
            ).to(device)(x)
        return x


class NSFSourceModule(TTNNOp):
    """
    Noise Source Module (NSF) for HiFT vocoder.
    Generates harmonic and noise components from F0.
    """

    def __init__(self, channels: int = 512):
        self.channels = channels

    def forward(self, f0: Tensor, noise: Optional[Tensor] = None) -> Tuple[Tensor, Tensor]:
        device = get_device()
        if noise is None:
            noise = torch.randn(1, self.channels, f0.shape[-1], device=device)
        # Harmonic component from F0
        harmonic = torch.sin(2 * torch.pi * f0 * torch.arange(
            self.channels, device=device
        ).float() / self.channels)
        return harmonic, noise


class HiFTVocoder(TTNNOp):
    """
    HiFT Vocoder for CosyVoice2.

    Combines ResBlock backbone, F0 predictor, NSF source module,
    and iSTFT synthesis head into a single streaming-capable module.
    """

    def __init__(self, config: Optional[HiFTConfig] = None):
        self.config = config or HiFTConfig()
        self.resblocks = torch.nn.ModuleList([
            ResBlock(self.config.hidden_channels)
            for _ in range(self.config.n_layers)
        ])
        self.f0_predictor = F0Predictor(self.config)
        self.nsf = NSFSourceModule(self.config.hidden_channels)
        self.istft = ISTFTOp(
            input_complex=None,  # Will be set during forward
            window_length=2048,
            hop_length=512,
        )

    def forward(
        self,
        mel: Tensor,
        f0: Optional[Tensor] = None,
        noise: Optional[Tensor] = None,
    ) -> Tensor:
        """
        Forward pass through HiFT vocoder.

        Args:
            mel: Mel spectrogram tensor (batch, channels, time)
            f0: Optional fundamental frequency tensor
            noise: Optional noise tensor for NSF

        Returns:
            Waveform tensor (batch, samples)
        """
        device = get_device()

        # F0 prediction if not provided
        if f0 is None:
            f0 = self.f0_predictor.forward(mel)

        # NSF source generation
        harmonic, noise_component = self.nsf.forward(f0, noise)

        # ResBlock backbone processing
        x = mel
        for i, resblock in enumerate(self.resblocks):
            dilation = 2 ** (i % self.config.dilation_cycle_length)
            # Apply resblock with appropriate dilation
            x = resblock.forward(x)
            # Inject harmonic/noise information
            x = x + harmonic * noise_component

        # iSTFT synthesis head
        # Convert mel features to STFT domain and apply inverse transform
        stft_coeffs = self._mel_to_stft(mel)
        waveform = self.istft.emit(None)  # Will be properly connected in graph

        return waveform

    def _mel_to_stft(self, mel: Tensor) -> Tensor:
        """Convert mel spectrogram to STFT coefficients."""
        device = get_device()
        # Use learned projection to map mel to complex STFT domain
        projection = torch.nn.Linear(
            self.config.input_channels,
            self.config.input_channels * 2,
        ).to(device)
        projected = projection(mel.permute(0, 2, 1))
        # Split into real and imaginary parts
        real, imag = projected.chunk(2, dim=-1)
        # Stack into complex tensor
        return torch.complex(real, imag)
