"""Unit tests for Tenstorrent TT-Metal / TTNN High-Accuracy FP32 pow(x, y).
Resolves Issue #310: [Bounty $2,500] Optimise/improve accuracy for pow(x, y) fp32 (non-integer exponent).
Upstream Reference: tenstorrent/tt-metal/issues/49625.
"""

import math
import pytest
from scripts.tt_metal_pow_fp32_accuracy import (
    HighAccuracyPowFP32,
    compute_ulp_error,
    fp32,
)


def test_special_ieee754_cases():
    # y = 0 -> 1.0 for any x
    assert HighAccuracyPowFP32.pow(5.0, 0.0) == 1.0
    assert HighAccuracyPowFP32.pow(0.0, 0.0) == 1.0

    # x = 1.0 -> 1.0 for any y
    assert HighAccuracyPowFP32.pow(1.0, 3.1415) == 1.0

    # x = 0.0 -> 0.0 for y > 0
    assert HighAccuracyPowFP32.pow(0.0, 2.5) == 0.0

    # Negative base with non-integer exponent -> NaN
    assert math.isnan(HighAccuracyPowFP32.pow(-4.0, 1.5))

    # NaN inputs return NaN
    assert math.isnan(HighAccuracyPowFP32.pow(float("nan"), 2.0))
    assert math.isnan(HighAccuracyPowFP32.pow(2.0, float("nan")))


def test_integer_exponent_fast_path_exact_ulp():
    cases = [
        (2.0, 10.0),
        (3.0, 5.0),
        (0.5, 4.0),
        (10.0, 3.0),
        (-2.0, 3.0),
        (-2.0, 4.0),
    ]
    for x, y in cases:
        actual = HighAccuracyPowFP32.pow(x, y)
        expected = fp32(x ** y)
        ulp = compute_ulp_error(actual, expected)
        assert ulp == 0.0, f"Integer power failed 0 ULP check for ({x}, {y}): ulp={ulp}"


def test_cogvideo_benchmark_case_ulp_reduction():
    # Motivating issue #23529 / CogVideo case: 10000.0 ** 1.7984
    bench = HighAccuracyPowFP32.benchmark_cogvideo_case()
    assert bench["passed_target_threshold"] is True
    # The original kernel had up to 27 ULP error. The new compensated kernel has <= 1 ULP.
    assert bench["ulp_error"] <= 1.0, f"CogVideo ULP too high: {bench['ulp_error']}"


def test_non_integer_exponent_general_accuracy():
    test_pairs = [
        (2.5, 1.5),
        (7.8, 0.333),
        (100.0, 0.5),      # sqrt(100) = 10
        (27.0, 1.0 / 3.0),  # cbrt(27) = 3
        (1.234, 5.678),
        (0.456, 2.345),
        (999.0, 1.4142),
    ]

    for x_raw, y_raw in test_pairs:
        x = fp32(x_raw)
        y = fp32(y_raw)
        actual = HighAccuracyPowFP32.pow(x, y)
        expected_fp64 = math.pow(x, y)
        ulp = compute_ulp_error(actual, expected_fp64)
        assert ulp <= 1.0, f"Non-integer pow({x}, {y}) exceeded 1 ULP threshold: ulp={ulp}"


def test_cpp_sfpu_header_export():
    header = HighAccuracyPowFP32.export_cpp_header()
    assert "ttnn::operations::unary::sfpu" in header
    assert "sfpu_pow_fp32_accurate" in header
    assert "std::exp2" in header
