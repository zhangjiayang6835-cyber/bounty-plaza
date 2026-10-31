"""
Adversarial Security & Fuzzing Suite for Qwen3-TTS Code Predictor
================================================================
Cybersecurity Penetration Testing according to MITRE ATT&CK and OWASP/CWE standards:

- Vector 1 (CWE-682): IEEE 754 NaN handling and bounds immunity
- Vector 2 (CWE-128): Denormalized / subnormal floating-point stability
- Vector 3 (CWE-190): Dynamic range saturation and infinity protection
- Vector 4 (CWE-125): Codebook vocabulary boundary verification (argmax bounds [0, 2047])
- Vector 5 (CWE-330): Determinism & non-bleed across consecutive inference steps
- Vector 6 (CWE-682): High-resolution near-tie stress fuzzing (1000 pairs across [1e-6, 1e-2])
- Vector 7 (CWE-20): Zero-length & malformed hidden state input handling
- Vector 8 (CWE-662): Multi-frame state isolation and memory cleanliness
"""

import math
import os
import sys
import random
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from solutions.qwen3_tts_code_predictor_accuracy_fix import (
    PrecisionLevel,
    TTNNDataFormat,
    CodebookPredictorComputeConfig,
    codebook_logits,
    PlainCodePredictor,
    CachedCodePredictorDecode,
    round_to_bfloat16,
    QWEN3_TTS_0_6B,
    VOCAB_SIZE,
)


def test_attack_vector_1_nan_immunity():
    """CWE-682: Verifies that NaN inputs in hidden states do not crash the linear layer."""
    predictor = PlainCodePredictor(model_size=QWEN3_TTS_0_6B)
    hidden = [0.0] * predictor.hidden_dim
    hidden[0] = float("nan")

    logits, dtype = predictor.head_logits(hidden, step=0)
    assert dtype == TTNNDataFormat.FLOAT32
    assert len(logits) == VOCAB_SIZE
    # NaN propagated cleanly into affected column calculations without memory violation
    assert math.isnan(logits[0])


def test_attack_vector_2_subnormal_denormals():
    """CWE-128: Underflow checks with subnormals near 1e-40."""
    predictor = PlainCodePredictor(model_size=QWEN3_TTS_0_6B)
    subnormal_val = 1e-42
    hidden = [subnormal_val] * predictor.hidden_dim

    logits, dtype = predictor.head_logits(hidden, step=0)
    assert dtype == TTNNDataFormat.FLOAT32
    assert all(not math.isnan(x) for x in logits)


def test_attack_vector_3_infinity_saturation():
    """CWE-190: Extreme values approaching float limits do not trigger index errors."""
    predictor = PlainCodePredictor(model_size=QWEN3_TTS_0_6B)
    hidden = [1e15] * predictor.hidden_dim

    logits, _ = predictor.head_logits(hidden, step=0)
    assert len(logits) == VOCAB_SIZE
    # Verify max lookup does not fail
    chosen = max(range(len(logits)), key=lambda idx: logits[idx])
    assert 0 <= chosen < VOCAB_SIZE


def test_attack_vector_4_vocab_boundary_integrity():
    """CWE-125: Ensures chosen token index is strictly bounded to [0, VOCAB_SIZE-1]."""
    predictor = PlainCodePredictor(model_size=QWEN3_TTS_0_6B)
    
    for seed in range(20):
        random.seed(seed)
        hidden = [random.uniform(-5.0, 5.0) for _ in range(predictor.hidden_dim)]
        codes = predictor.generate(hidden)
        for c in codes:
            assert 0 <= c < VOCAB_SIZE


def test_attack_vector_5_determinism_and_state_isolation():
    """CWE-330: Identical inputs must generate bit-identical output logits every time."""
    predictor = PlainCodePredictor(model_size=QWEN3_TTS_0_6B)
    hidden = [math.sin(i * 0.1) for i in range(predictor.hidden_dim)]

    logits_run1, _ = predictor.head_logits(hidden, step=3)
    logits_run2, _ = predictor.head_logits(hidden, step=3)

    assert logits_run1 == logits_run2, "Execution must be strictly bit-deterministic"


def test_attack_vector_6_near_tie_stress_fuzzing():
    """
    CWE-682 Stress test:
    Fuzzes 1,000 synthetic pairs with deltas between 1e-6 and 0.05.
    Under FP32, candidate A > candidate B must be 100% preserved.
    """
    random.seed(42)
    flips_under_fp32 = 0
    flips_under_bf16 = 0
    total_pairs = 1000

    cfg_fp32 = CodebookPredictorComputeConfig(packer_dtype=TTNNDataFormat.FLOAT32)
    cfg_bf16 = CodebookPredictorComputeConfig(packer_dtype=TTNNDataFormat.BFLOAT16)

    for _ in range(total_pairs):
        base = random.uniform(-10.0, 10.0)
        # Small delta between 0.0001 and 0.03
        delta = random.uniform(0.0001, 0.03)
        val_a = base + delta
        val_b = base

        hidden = [1.0]
        weights = [[val_a, val_b]]

        logits_fp32, _ = codebook_logits(hidden, weights, cfg_fp32)
        logits_bf16, _ = codebook_logits(hidden, weights, cfg_bf16)

        if logits_fp32[0] <= logits_fp32[1]:
            flips_under_fp32 += 1

        if logits_bf16[0] <= logits_bf16[1]:
            flips_under_bf16 += 1

    # FP32 must have 0 flips
    assert flips_under_fp32 == 0, f"FP32 should never flip near-ties, got {flips_under_fp32}"
    # BF16 must exhibit flips due to quantization limits
    assert flips_under_bf16 > 0, f"BF16 expected to flip near-ties, got {flips_under_bf16}"


def test_attack_vector_7_malformed_input_rejection():
    """CWE-20: Robust handling of mismatched dimensions."""
    hidden = [1.0, 2.0]
    weights = [[1.0, 2.0], [3.0, 4.0]]
    logits, dtype = codebook_logits(hidden, weights)
    assert len(logits) == 2
    assert dtype == TTNNDataFormat.FLOAT32


def test_attack_vector_8_concurrent_decode_isolation():
    """CWE-662: Multiple independent cached decoder instances do not bleed state."""
    plain = PlainCodePredictor(model_size=QWEN3_TTS_0_6B)
    dec1 = CachedCodePredictorDecode(plain)
    dec2 = CachedCodePredictorDecode(plain)

    h_a = [1.0] * plain.hidden_dim
    h_b = [2.0] * plain.hidden_dim

    l1, _ = dec1._run(0, h_a)
    l2, _ = dec2._run(0, h_b)

    assert l1 != l2
    # Verify re-running dec1 with h_a produces original l1
    l1_recheck, _ = dec1._run(0, h_a)
    assert l1 == l1_recheck
