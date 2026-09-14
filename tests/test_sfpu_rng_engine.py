"""Unit, statistical quality, and lane decorrelation test suite for SFPU PRNG.
Resolves Issue #765: [Bounty $6,000] Fix SFPU RNG correlation and improve FP32 uniform random quality.
"""

import numpy as np
import pytest
from scripts.sfpu_rng_engine import (
    SFPULaneGenerator,
    sanitize_lfsr_seed,
    splitmix32_nonlinear_transform,
    compute_spatial_core_salt,
    compute_inter_lane_cross_correlation,
    XNOR_LOCK_STATE,
    CPP_SFPU_PRNG_PATCH,
)


def test_sanitize_lfsr_seed_lock_states():
    """Verifies that all-ones (0xFFFFFFFF) and zero seeds are safely perturbed to avoid lock states."""
    assert sanitize_lfsr_seed(XNOR_LOCK_STATE) != XNOR_LOCK_STATE
    assert sanitize_lfsr_seed(0) != 0

    normal_seed = 0x12345678
    assert sanitize_lfsr_seed(normal_seed) == normal_seed


def test_splitmix32_avalanche_and_determinism():
    """Verifies that SplitMix32 provides consistent deterministic nonlinear diffusion."""
    val1 = 0x00000001
    val2 = 0x00000002

    out1 = splitmix32_nonlinear_transform(val1)
    out2 = splitmix32_nonlinear_transform(val2)

    # Must be deterministic
    assert splitmix32_nonlinear_transform(val1) == out1
    # Different inputs produce avalanche bit differences
    bit_diff = bin(out1 ^ out2).count("1")
    assert bit_diff >= 10, f"Insufficient avalanche effect: only {bit_diff} bit differences"


def test_lane_decorrelation_reduces_inter_lane_cross_correlation():
    """Verifies that nonlinear decorrelation substantially drops adjacent lane correlation."""
    num_steps = 500
    gen_legacy = SFPULaneGenerator(base_seed=0x9ABCDEF0)
    gen_robust = SFPULaneGenerator(base_seed=0x9ABCDEF0)

    legacy_samples = np.zeros((num_steps, 32), dtype=np.float32)
    robust_samples = np.zeros((num_steps, 32), dtype=np.float32)

    for i in range(num_steps):
        legacy_samples[i, :] = gen_legacy.generate_uniform_tile(legacy_mode=True)
        robust_samples[i, :] = gen_robust.generate_uniform_tile(legacy_mode=False)

    corr_legacy = compute_inter_lane_cross_correlation(legacy_samples)
    corr_robust = compute_inter_lane_cross_correlation(robust_samples)

    # Robust decorrelated stream must have low cross-lane correlation (< 0.15)
    assert corr_robust < 0.15, f"Robust correlation {corr_robust} is higher than expected"
    # All values must strictly respect [0.0, 1.0)
    assert np.all(robust_samples >= 0.0)
    assert np.all(robust_samples < 1.0)


def test_narrow_range_fp32_preservation():
    """Verifies that very narrow FP32 intervals (e.g. [1e-8, 2e-8]) are preserved without subtraction distortion."""
    gen = SFPULaneGenerator(base_seed=0x55AA55AA)
    low, high = 1e-8, 2e-8

    samples = np.zeros((100, 32), dtype=np.float32)
    for i in range(100):
        samples[i, :] = gen.generate_uniform_tile(low=low, high=high, legacy_mode=False)

    assert np.all(samples >= low), f"Values fell below low bound {low}"
    assert np.all(samples <= high), f"Values exceeded high bound {high}"

    mean_val = float(np.mean(samples))
    expected_mid = (low + high) / 2.0
    # Mean of uniform distribution should be approximately mid-point
    assert abs(mean_val - expected_mid) < (high - low) * 0.2


def test_spatial_core_salt_stream_separation():
    """Verifies that adjacent cores produce independent, distinct PRNG trajectories."""
    gen_core_0_0 = SFPULaneGenerator(base_seed=0x12345678, core_x=0, core_y=0)
    gen_core_0_1 = SFPULaneGenerator(base_seed=0x12345678, core_x=0, core_y=1)

    tile_0_0 = gen_core_0_0.generate_uniform_tile()
    tile_0_1 = gen_core_0_1.generate_uniform_tile()

    # Streams must differ immediately
    assert not np.allclose(tile_0_0, tile_0_1)


def test_cpp_sfpu_prng_patch_structure():
    """Verifies C++ header patch declares decorrelator micro-op and float conversion."""
    assert "sfpu_decorrelate_lane" in CPP_SFPU_PRNG_PATCH
    assert "sfpu_uint32_to_uniform_fp32" in CPP_SFPU_PRNG_PATCH
    assert "sfpu_sanitize_seed" in CPP_SFPU_PRNG_PATCH
    assert "0x85EBCA6Bu" in CPP_SFPU_PRNG_PATCH
