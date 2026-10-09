```python
# Copyright 2024 Tenstorrent AI ULC
#
# Licensed under the Apache License v2.0 with LLVM exceptions.
# See https://llvm.org/foundation/releases.html#licensing for details.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""
Tests for iSTFT operation and HiFT vocoder.
Validates correctness against reference implementation.
"""

import pytest
import torch
from ttmetal.dialects.ttnn.operations.istft import ISTFTOp
from ttmetal.dialects.ttnn.operations.hift_vocoder import HiFTVocoder, HiFTConfig
from ttmetal.dialects.ttnn.operations.cosyvoice2_pipeline import CosyVoice2Pipeline, CosyVoice2Config


class TestISTFTOp:
    """Tests for iSTFT operation."""

    def test_istft_basic(self):
        """Test basic iSTFT reconstruction."""
        device = torch.device("cuda")
        window_length = 2048
        hop_length = 512

        # Create test STFT coefficients
        batch = 1
        freq_bins = window_length // 2 + 1
        time_frames = 10
        stft_coeffs = torch.randn(batch, freq_bins, time_frames, device=device).complex()

        # Create iSTFT op
        istft = ISTFTOp(
            input_complex=stft_coeffs,
            window_length=window_length,
            hop_length=hop_length,
        )

        # Forward pass
        output = istft.emit(None)

        # Validate output shape
        expected_length = time_frames * hop_length + window_length
        assert output.shape[-1] == expected_length

    def test_istft_reconstruction(self):
        """Test that iSTFT can reconstruct a simple signal."""
        device = torch.device("cuda")
        sample_rate = 16000
        duration = 0.5  # seconds
        window_length = 1024
        hop_length = 256

        # Create a simple sine wave
        t = torch.linspace(0, duration, int(sample_rate * duration), device=device)
        freq = 440.0  # A4 note
        signal = torch.sin(2 * torch.pi * freq * t)

        # Compute STFT using torch
        stft = torch.stft(
            signal,
            n_fft=window_length,
            hop_length=hop_length,
            window=torch.hann_window(window_length, device=device),
            return_complex=True
        )

        # Reconstruct using iSTFT
        reconstructed = torch.istft(
            stft,
            n_fft=window_length,
            hop_length=hop_length,
            window=torch.hann_window(window_length, device=device),
            length=len(signal)
        )

        # Compare with our implementation
        istft = ISTFTOp(
            input_complex=stft.unsqueeze(0),
            window_length=window_length,
            hop_length=hop_length,
        )
        output = istft.emit(None)

        # Check similarity (allow some numerical difference)
        assert torch.allclose(
            output.flatten(), reconstructed, atol=1e-3
        ), "iSTFT reconstruction failed"


class TestHiFTVocoder:
    """Tests for HiFT vocoder."""

    def test_hift_forward(self):
        """Test HiFT vocoder forward pass."""
        device = torch.device("cuda")
        config = HiFTConfig()
        vocoder = HiFTVocoder(config)

        # Create test mel spectrogram
        batch = 1
        mel_channels = config.input_channels
        mel_length = 100
        mel = torch.randn(batch, mel_channels, mel_length, device=device)

        # Forward pass
        waveform = vocoder.forward(mel)

        # Validate output
        assert waveform is not None
        assert waveform.dim() == 2  # (batch, samples)

    def test_hift_with_f0(self):
        """Test HiFT vocoder with explicit F0 input."""
        device = torch.device("cuda")
        config = HiFTConfig()
        vocoder = HiFTVocoder(config)

        mel = torch.randn(1, config.input_channels, 50, device=device)
        f0 = torch.randn(1, 1, 50, device=device)

        waveform = vocoder.forward(mel, f0=f0)

        assert waveform is not None
        assert waveform.shape[0] == 1


class TestCosyVoice2Pipeline:
    """Tests for complete CosyVoice2 pipeline."""

    def test_pipeline_streaming(self):
        """Test streaming synthesis pipeline."""
        device = torch.device("cuda")
        config = CosyVoice2Config()
        pipeline = CosyVoice2Pipeline(config)

        text = "Hello world. This is a test."

        # Collect streamed output
        chunks = list(pipeline.synthesize_streaming(text))

        assert len(chunks) > 0
        for chunk, is_final in chunks:
            assert chunk is not None
            assert isinstance(is_final, bool)

    def test_pipeline_pcc_evaluation(self):
        """Test PCC evaluation method."""
        device = torch.device("cuda")
        config = CosyVoice2Config()
        pipeline = CosyVoice2Pipeline(config)

        # Create reference and synthetic waveforms
        ref = torch.randn(1, 1000, device=device)
        synth = ref + 0.01 * torch.randn_like(ref)  # Slightly noisy version

        # High PCC expected
        result = pipeline.evaluate_pcc(ref, synth, tolerance=0.95)
        assert result is True

        # Low PCC expected
        noisy = torch.randn_like(ref)
        result = pipeline.evaluate_pcc(ref, noisy, tolerance=0.99)
        assert result is False

    def test_pipeline_latency_measurement(self):
        """Test latency and RTF measurement."""
        device = torch.device("cuda")
        config = CosyVoice2Config()
        pipeline = CosyVoice2Pipeline(config)

        text = "Test text for latency measurement."

        metrics = pipeline.measure_latency_and_rtf(text, num_runs=3)

        assert "avg_latency_ms" in metrics
        assert "rtf" in metrics
        assert metrics["avg_latency_ms"] > 0
        assert metrics["rtf"] > 0
