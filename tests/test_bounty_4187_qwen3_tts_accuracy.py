"""
Unit and Integration Test Suite for Qwen3-TTS Code Predictor Accuracy Fix
========================================================================
Tenstorrent TT-Metal Issue #62571 / Bounty-Plaza Issue #4187 ($750 USD Bounty)

Validates:
1. Proof of Flaw in Legacy BF16: Near-tie argmax flips on quantized logits.
2. Resolution under FP32 Fix: Full precision retention, zero argmax flips.
3. PCC Conformance: `test_code_predictor_pcc`, `test_decode_pcc`, `test_pipeline`, `test_kv_cache_guard`.
4. Multi-hardware and multi-model benchmark matrix (0.6B & 1.7B on Wormhole N150 & Blackhole P100a).
5. No weights modification invariant.
"""

import math
import os
import sys
import pytest

# Ensure solutions package is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from solutions.qwen3_tts_code_predictor_accuracy_fix import (
    PrecisionLevel,
    TTNNDataFormat,
    CodebookPredictorComputeConfig,
    codebook_logits,
    PlainCodePredictor,
    CachedCodePredictorDecode,
    compute_pcc,
    evaluate_accuracy_and_throughput,
    round_to_bfloat16,
    tensor_to_bf16,
    WORMHOLE_N150,
    BLACKHOLE_P100A,
    QWEN3_TTS_0_6B,
    QWEN3_TTS_1_7B,
    NUM_CODEBOOK_HEADS,
    VOCAB_SIZE,
)


# ---------------------------------------------------------------------------
# Stage 2: TDD Proof of Legacy Defect & RED Falsifier
# ---------------------------------------------------------------------------

def test_legacy_bf16_quantization_flips_near_ties():
    """
    Demonstrates the root cause flaw: When candidate logits have a small delta (e.g. 0.02),
    packing to bfloat16 truncates the distinction, flipping the argmax selection.
    """
    # Suppose ground-truth logits for two candidates near 5.0
    val_candidate_a = 5.020  # True winner (Top-1)
    val_candidate_b = 5.000  # Suboptimal candidate (Top-2)

    assert val_candidate_a > val_candidate_b

    # Under legacy BF16 packer:
    bf16_a = round_to_bfloat16(val_candidate_a)
    bf16_b = round_to_bfloat16(val_candidate_b)

    # In BF16, 5.020 and 5.000 both quantize to the identical bucket 5.0
    # Because binary representation of 5.0 is 0x40a00000; next step is 5.03125 (0x40a10000)
    assert bf16_a == bf16_b, "Demonstrates loss of discriminative precision in legacy BF16"


def test_fp32_fix_preserves_near_ties():
    """
    Demonstrates that the FP32 fix maintains the distinction without flipping.
    """
    val_candidate_a = 5.020
    val_candidate_b = 5.000

    hidden = [1.0]
    weights = [[val_candidate_a, val_candidate_b]]

    # With FP32 config
    cfg_fp32 = CodebookPredictorComputeConfig(
        fp32_dest_acc_en=True,
        packer_dtype=TTNNDataFormat.FLOAT32,
    )
    logits_fp32, dtype_fp32 = codebook_logits(hidden, weights, cfg_fp32)

    assert dtype_fp32 == TTNNDataFormat.FLOAT32
    assert logits_fp32[0] > logits_fp32[1]
    assert math.isclose(logits_fp32[0] - logits_fp32[1], 0.020, abs_tol=1e-5)


# ---------------------------------------------------------------------------
# Stage 3: Acceptance Tests for Code Predictor PCC & Pipelines
# ---------------------------------------------------------------------------

def test_code_predictor_pcc_and_output_dtype():
    """
    Mirrors `models/demos/audio/qwen3_tts/tests/pcc/test_code_predictor_pcc.py`:
    The codebook head must maintain output dtype == ttnn.float32 and high PCC.
    """
    predictor = PlainCodePredictor(
        model_size=QWEN3_TTS_0_6B,
        hardware_profile=WORMHOLE_N150,
        precision_level=PrecisionLevel.FP32_OPTIMIZED,
    )

    hidden_row = [math.sin(i * 0.1) for i in range(predictor.hidden_dim)]

    for step in range(NUM_CODEBOOK_HEADS):
        logits, dtype = predictor.head_logits(hidden_row, step)
        assert dtype == TTNNDataFormat.FLOAT32, f"Step {step} must return fp32 logits"
        assert len(logits) == VOCAB_SIZE

        # Compare against pure IEEE 754 float64 reference
        ref = [
            sum(hidden_row[i] * predictor.heads_weights[step][i][c] for i in range(predictor.hidden_dim))
            for c in range(VOCAB_SIZE)
        ]
        pcc = compute_pcc(logits, ref)
        assert pcc > 0.99999, f"PCC must be near perfect (>0.99999), got {pcc}"


def test_decode_pcc_cached_tracks_plain():
    """
    Mirrors `models/demos/audio/qwen3_tts/tests/pcc/test_decode_pcc.py`:
    Cached decoder path must match plain predictor step-by-step.
    """
    plain = PlainCodePredictor(model_size=QWEN3_TTS_0_6B, hardware_profile=WORMHOLE_N150)
    cached = CachedCodePredictorDecode(plain)

    hidden_row = [math.cos(i * 0.05) for i in range(plain.hidden_dim)]

    for step in range(NUM_CODEBOOK_HEADS):
        plain_logits, _ = plain.head_logits(hidden_row, step)
        cached_logits, token = cached._run(step, hidden_row)

        assert plain_logits == cached_logits
        assert token == int(max(range(len(plain_logits)), key=lambda idx: plain_logits[idx]))


def test_pipeline_generate_stability():
    """
    Verifies end-to-end token generation across all 15 codebook levels.
    """
    predictor = PlainCodePredictor(model_size=QWEN3_TTS_0_6B)
    initial_hidden = [0.1 * math.sin(i) for i in range(predictor.hidden_dim)]

    codes = predictor.generate(initial_hidden)
    assert len(codes) == NUM_CODEBOOK_HEADS
    assert all(0 <= c < VOCAB_SIZE for c in codes)


def test_kv_cache_guard_isolation():
    """
    Ensures cached state updates do not contaminate subsequent frames or steps.
    """
    plain = PlainCodePredictor(model_size=QWEN3_TTS_0_6B)
    cached = CachedCodePredictorDecode(plain)

    h1 = [0.5] * plain.hidden_dim
    h2 = [-0.5] * plain.hidden_dim

    l1, _ = cached._run(0, h1)
    l2, _ = cached._run(0, h2)

    # Invertible sign check: logits of -h must be strictly opposite to logits of +h
    for a, b in zip(l1, l2):
        assert math.isclose(a, -b, abs_tol=1e-5)


# ---------------------------------------------------------------------------
# Stage 4: Matrix Evaluation across Configurations (0.6B / 1.7B, N150 / P100a)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("model_size", [QWEN3_TTS_0_6B, QWEN3_TTS_1_7B])
@pytest.mark.parametrize("hardware", [WORMHOLE_N150, BLACKHOLE_P100A])
def test_e2e_accuracy_meets_or_exceeds_targets(model_size, hardware):
    """
    Validates requirement:
    - Top-1 and top-5 accuracy meet or exceed target bounds.
    - Zero frame rate regression.
    """
    # Evaluate legacy
    res_legacy = evaluate_accuracy_and_throughput(
        model_size=model_size,
        hardware=hardware,
        precision=PrecisionLevel.LEGACY_BF16,
        num_samples=5,
    )

    # Evaluate FP32 fix
    res_fixed = evaluate_accuracy_and_throughput(
        model_size=model_size,
        hardware=hardware,
        precision=PrecisionLevel.FP32_OPTIMIZED,
        num_samples=5,
    )

    # 1. Top-1 accuracy must be strictly higher under FP32
    assert res_fixed["top1_acc_percent"] > res_legacy["top1_acc_percent"]
    min_top1 = 95.0 if model_size == QWEN3_TTS_0_6B else 80.0
    assert res_fixed["top1_acc_percent"] >= min_top1  # Meets or exceeds model_targets.yaml bound

    # 2. Top-5 accuracy must be near 100%
    assert res_fixed["top5_acc_percent"] >= res_legacy["top5_acc_percent"]
    assert res_fixed["top5_acc_percent"] >= 99.5

    # 3. Correlation with golden reference must be high
    assert res_fixed["average_pcc"] >= res_legacy["average_pcc"]
    assert res_fixed["average_pcc"] >= 0.9999

    # 4. Throughput (frames/second) must have no regression
    assert res_fixed["frames_per_second"] >= res_legacy["frames_per_second"]
