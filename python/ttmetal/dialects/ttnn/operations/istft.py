```python
# Copyright 2024 Tenstorrent AI ULC
#
# Licensed under the Apache License v2.0 with LLVM exceptions.
# See https://llvm.org/foundation/releases.html#licensing for details.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""
iSTFT (inverse Short-Time Fourier Transform) operation for TTNN.

Implements matmul-based inverse DFT using precomputed weight matrices
against real/imaginary component tensors. Used by the HiFT vocoder
synthesis head in CosyVoice2 streaming pipeline.
"""

from __future__ import annotations

from typing import Optional

import torch
from ttmetal.dialects.ttnn.operations.core import TTNNOp
from ttmetal.dialects.ttnn.types import Tensor, Shape
from ttmetal.dialects.ttnn.utils import get_device


class ISTFTOp(TTNNOp):
    """
    Inverse Short-Time Fourier Transform.

    Reconstructs time-domain waveform from STFT coefficients using
    overlap-add with hamming window. Implemented as matmul against
    precomputed inverse DFT basis matrices.
    """

    op_name = "istft"

    def __init__(
        self,
        input_complex: Tensor,
        window_length: int,
        hop_length: int,
        window: Optional[Tensor] = None,
        center: bool = True,
        normalized: bool = False,
        onesided: bool = True,
        return_complex: bool = True,
    ):
        self.input_complex = input_complex
        self.window_length = window_length
        self.hop_length = hop_length
        self.window = window
        self.center = center
        self.normalized = normalized
        self.onesided = onesided
        self.return_complex = return_complex

    @classmethod
    def describe(cls, **kwargs) -> dict:
        return {
            "operation": cls.op_name,
            "inputs": ["input_complex"],
            "attributes": {
                "window_length": kwargs.get("window_length", 2048),
                "hop_length": kwargs.get("hop_length", 512),
                "center": kwargs.get("center", True),
                "normalized": kwargs.get("normalized", False),
                "onesided": kwargs.get("onesided", True),
                "return_complex": kwargs.get("return_complex", True),
            },
        }

    def emit(self, dispatcher) -> Tensor:
        """
        Emit the iSTFT operation using matmul-based inverse DFT.

        The inverse DFT is computed as:
          X[k] = sum_n x[n] * exp(j*2*pi*k*n/N)
        
        For iSTFT, we use precomputed complex exponential basis matrices
        and perform matmul operations on real/imaginary components.
        """
        device = get_device()
        window_length = self.window_length
        hop_length = self.hop_length

        # Precompute inverse DFT basis matrix
        # Shape: (window_length, freq_bins)
        n = torch.arange(window_length).float()
        k = torch.arange(0, window_length // 2 + 1).float()
        # Complex exponential for inverse DFT
        basis = torch.exp(
            1j * 2.0 * torch.pi * torch.outer(k, n) / window_length
        )

        # Perform matmul-based inverse DFT on each frame
        input_tensor = self.input_complex
        # input shape: (batch, freq_bins, time_frames)
        batch, freq_bins, time_frames = input_tensor.shape

        # Reshape and apply inverse DFT via matmul
        # (batch * time_frames, freq_bins) @ (freq_bins, window_length)
        reshaped = input_tensor.permute(0, 2, 1).reshape(-1, freq_bins)
        output_frames = reshaped @ basis.real

        # Overlap-add with window compensation
        output_length = time_frames * hop_length + window_length
        output = torch.zeros(batch, output_length, device=device)

        # Window normalization for overlap-add
        if self.window is not None:
            win = self.window
        else:
            win = torch.hann_window(window_length, device=device)

        # Accumulate frames with overlap-add
        for t in range(time_frames):
            start = t * hop_length
            end = start + window_length
            output[:, start:end] += output_frames[:, t * window_length:(t + 1) * window_length] * win

        return Tensor(output, shape=Shape([batch, output_length]))
