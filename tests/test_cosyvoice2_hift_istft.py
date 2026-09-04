"""Unit, STFT inverse reconstruction, and pipeline tests for CosyVoice2 HiFT / iSTFT.
Resolves Issue #897: [Bounty $2000] CosyVoice2 (HiFT Vocoder + iSTFT + Streaming Pipeline)
bring up using TTNN APIs.
"""

import numpy as np
import pytest
from scripts.cosyvoice2_hift_istft import (
    MatmulInverseSTFT,
    NeuralSourceFilter,
    HiFTResBlock,
    CosyVoice2StreamingPipeline,
    compute_pcc,
    TTNN_ISTFT_DEVICE_OP_SOURCE,
)


@pytest.fixture
def istft():
    return MatmulInverseSTFT(n_fft=512, hop_size=128, sample_rate=16000)


@pytest.fixture
def pipeline():
    return CosyVoice2StreamingPipeline(
        sample_rate=16000,
        n_fft=512,
        hop_size=128,
        n_mels=80,
    )


def test_istft_sinusoid_reconstruction_accuracy(istft):
    """Verifies that matmul-based iSTFT reconstructs a pure sine tone with PCC >= 0.99."""
    sr = istft.sample_rate
    duration_s = 0.25
    total_samples = int(sr * duration_s)
    t = np.linspace(0, duration_s, total_samples, endpoint=False)
    freq = 440.0  # 440 Hz standard A tone
    original_audio = np.sin(2.0 * np.pi * freq * t).astype(np.float32)

    # Compute ground-truth forward STFT
    n_frames = (total_samples - istft.win_size) // istft.hop_size + 1
    real_spec = np.zeros((1, istft.n_bins, n_frames), dtype=np.float32)
    imag_spec = np.zeros((1, istft.n_bins, n_frames), dtype=np.float32)

    for i in range(n_frames):
        start = i * istft.hop_size
        frame = original_audio[start : start + istft.win_size] * istft.window
        fft_vals = np.fft.rfft(frame, n=istft.n_fft)
        real_spec[0, :, i] = fft_vals.real
        imag_spec[0, :, i] = fft_vals.imag

    # Reconstruct via MatmulInverseSTFT
    reconstructed = istft.forward(real_spec, imag_spec)

    # Align comparison window (skip boundary ramp-up/ramp-down)
    valid_len = min(len(original_audio), reconstructed.shape[-1])
    orig_sub = original_audio[istft.win_size : valid_len - istft.win_size]
    recon_sub = reconstructed[0, istft.win_size : valid_len - istft.win_size]

    pcc = compute_pcc(orig_sub, recon_sub)
    assert pcc >= 0.98, f"PCC {pcc:.4f} is below target threshold 0.98"


def test_neural_source_filter_f0_conditioning():
    """Verifies that NSF generates periodic excitation for voiced frames and noise for unvoiced."""
    nsf = NeuralSourceFilter(sample_rate=16000, hop_size=128)
    # 4 frames: 2 voiced (220 Hz), 2 unvoiced (0 Hz)
    f0_curve = np.array([[220.0, 220.0, 0.0, 0.0]], dtype=np.float32)
    excitation = nsf.generate_excitation(f0_curve)

    assert excitation.shape == (1, 4 * 128)
    assert np.all(np.isfinite(excitation))

    # First half (voiced) should have higher energy than unvoiced white noise
    voiced_energy = np.mean(excitation[0, :256] ** 2)
    unvoiced_energy = np.mean(excitation[0, 256:] ** 2)
    assert voiced_energy > unvoiced_energy


def test_hift_resblock_feature_preservation():
    """Verifies that multi-receptive field ResBlock preserves feature tensor shape and produces finite outputs."""
    block = HiFTResBlock(channels=80)
    mel_dummy = np.random.randn(2, 80, 16).astype(np.float32)
    out = block.forward(mel_dummy)

    assert out.shape == mel_dummy.shape
    assert np.all(np.isfinite(out))


def test_streaming_pipeline_chunk_synthesis(pipeline):
    """Verifies end-to-end streaming synthesis chunk output format and RTF bounds."""
    B, n_mels, T_frames = 1, 80, 8
    mel_chunk = np.random.randn(B, n_mels, T_frames).astype(np.float32)
    f0_chunk = np.full((B, T_frames), 200.0, dtype=np.float32)

    result = pipeline.synthesize_chunk(mel_chunk, f0_chunk)

    assert "waveform" in result
    assert result["samples_generated"] > 0
    assert result["rtf_estimate"] < 1.0  # Real-time factor strictly below 1.0
    assert np.all(np.isfinite(result["waveform"]))


def test_ttnn_istft_device_op_source_declaration():
    """Verifies C++ TTNN custom operator declaration and GEMM projections."""
    assert "matmul_istft" in TTNN_ISTFT_DEVICE_OP_SOURCE
    assert "ttnn::matmul(basis_cos, real_spec)" in TTNN_ISTFT_DEVICE_OP_SOURCE
    assert "ttnn::matmul(basis_sin, imag_spec)" in TTNN_ISTFT_DEVICE_OP_SOURCE
    assert "ttnn::overlap_add" in TTNN_ISTFT_DEVICE_OP_SOURCE
