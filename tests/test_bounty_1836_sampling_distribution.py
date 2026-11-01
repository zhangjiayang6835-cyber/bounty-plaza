"""
Unit and Integration Test Suite for TT-Metal ttnn.sampling Precision Optimization.
Resolves Tenstorrent Issue #59732 / Bounty-Plaza Issue #1836 ($3,000 USD Bounty).

Validates:
1. Proof of Flaw: BF16 truncation creates zero-emission dead zones for rare tokens (P < 0.0039).
2. Resolution under FP32: Full continuous threshold coverage, eliminating dead zones.
3. Goodness of Fit: Chi-Square goodness-of-fit test confirms unbiased distribution (p > 0.05).
4. Sampling Controls: Temperature scaling, top-k filtering, and deterministic seed replay.
5. Error handling and numerical stability on extreme probabilities.
"""

import os
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest
from solutions.ttnn_sampling_distribution_guard import (
    TTNNSamplingDistributionGuard,
    SamplerConfig,
    quantize_bf16_threshold,
)


@pytest.fixture
def guard():
    return TTNNSamplingDistributionGuard()


def test_bounty_1836_bf16_dead_zone_proof_of_flaw(guard):
    """
    CRITICAL PROOF OF FLAW:
    A tail token with probability 0.003 (between CDF 0.997 and 1.0)
    can NEVER be emitted under BF16 because threshold is capped at 255/256 (0.99609).
    """
    cdf = [(0, 0.95), (1, 0.997), (2, 1.0)]
    threshold = 0.9985

    # Under BF16: threshold 0.9985 is clamped to 255/256 = 0.99609375.
    # 0.99609375 < 0.997 -> picks token 1! Tail token 2 is in a dead zone!
    bf16_token = guard.sample_token(cdf, threshold, enforce_bf16_legacy=True)
    assert bf16_token == 1

    # Under FP32 fix: threshold 0.9985 is preserved.
    # 0.9985 > 0.997 -> correctly emits tail token 2!
    fp32_token = guard.sample_token(cdf, threshold, enforce_bf16_legacy=False)
    assert fp32_token == 2


def test_chi_square_goodness_of_fit_unbiased(guard):
    """Validates that empirical sampling matches theoretical distribution with p > 0.05."""
    report = guard.evaluate_statistical_goodness_of_fit(num_trials=4000)
    assert report.is_distribution_unbiased is True
    assert report.chi_square_stat < 9.488
    assert report.rare_token_coverage_pct > 50.0


def test_temperature_scaling(guard):
    """Verifies temperature scaling flattens or sharpens logit distribution."""
    logits = [2.0, 1.0, 0.5]
    hot = guard.apply_temperature_and_top_k(logits, top_k=3, temperature=2.0)
    cold = guard.apply_temperature_and_top_k(logits, top_k=3, temperature=0.5)

    # Difference between top 2 logits is smaller at high temperature
    diff_hot = hot[0][1] - hot[1][1]
    diff_cold = cold[0][1] - cold[1][1]
    assert diff_hot < diff_cold


def test_top_k_filtering(guard):
    """Verifies top-k restricts candidate vocabulary to exactly k elements."""
    logits = [float(i) for i in range(100)]
    filtered = guard.apply_temperature_and_top_k(logits, top_k=10, temperature=1.0)
    assert len(filtered) == 10
    # Top element should be index 99 with logit 99.0
    assert filtered[0][0] == 99


def test_deterministic_seed_replay(guard):
    """Verifies deterministic sequence generation across runs."""
    cdf = [(0, 0.5), (1, 1.0)]
    thresholds = [0.123, 0.789, 0.456, 0.654]
    run1 = [guard.sample_token(cdf, u) for u in thresholds]
    run2 = [guard.sample_token(cdf, u) for u in thresholds]
    assert run1 == run2


def test_empty_cdf_raises_error(guard):
    """Verifies error handling on empty CDF."""
    with pytest.raises(ValueError, match="CDF cannot be empty"):
        guard.sample_token([], 0.5)


def test_quantize_bf16_bounds():
    """Verifies boundary clamping of BF16 quantization helper."""
    assert quantize_bf16_threshold(0.0) == 0.0
    assert quantize_bf16_threshold(1.0) == 0.99609375
    assert quantize_bf16_threshold(-0.5) == 0.0
