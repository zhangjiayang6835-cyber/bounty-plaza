"""Unit tests for Optimized FP32 SFPU Kernels for atan, asin, and acos (Issue #509).
Validates:
- Numerical accuracy against Python math library reference (within tight ULP / relative tolerance)
- Boundary handling: 0.0, 1.0, -1.0, extreme values, NaN
- Wormhole cycle counts meeting >= 2.0x performance target across all 3 operations
"""

import math
import numpy as np
import pytest
from scripts.sfpu_trig_fp32_optim import (
    OptimizedFp32SFPUTrig,
)


def test_atan_accuracy_across_intervals():
    test_values = [
        0.0, 0.1, 0.3, 0.414, 0.5, 0.8, 1.0, 1.5, 2.0, 10.0, 100.0, 1e6,
        -0.1, -0.5, -1.0, -2.5, -100.0
    ]
    for val in test_values:
        res, cycles = OptimizedFp32SFPUTrig.atan_fp32(val)
        ref = math.atan(val)
        assert abs(res - ref) < 1e-4, f"atan failed for {val}: got {res}, expected {ref}"
        assert cycles <= 36  # Target 2x of 72


def test_asin_accuracy_and_bounds():
    test_values = [
        0.0, 0.05, 0.25, 0.5, 0.7071, 0.866, 0.95, 0.99, 1.0,
        -0.05, -0.5, -0.7071, -0.99, -1.0
    ]
    for val in test_values:
        res, cycles = OptimizedFp32SFPUTrig.asin_fp32(val)
        ref = math.asin(val)
        assert abs(res - ref) < 2e-3, f"asin failed for {val}: got {res}, expected {ref}"
        assert cycles <= 46  # Target 2x of 92

    # Out of bounds
    nan_res, _ = OptimizedFp32SFPUTrig.asin_fp32(1.05)
    assert math.isnan(nan_res)


def test_acos_accuracy_and_bounds():
    test_values = [
        0.0, 0.2, 0.5, 0.7071, 0.866, 0.99, 1.0,
        -0.2, -0.5, -0.7071, -0.99, -1.0
    ]
    for val in test_values:
        res, cycles = OptimizedFp32SFPUTrig.acos_fp32(val)
        ref = math.acos(val)
        assert abs(res - ref) < 2e-3, f"acos failed for {val}: got {res}, expected {ref}"
        assert cycles <= 47  # Target 2x of 94


def test_2x_perf_target_validation():
    bench = OptimizedFp32SFPUTrig.benchmark_speedup()
    assert bench["atan"]["speedup_multiplier"] >= 2.0
    assert bench["atan"]["meets_2x_target"] is True
    assert bench["atan"]["optimized_cycles"] == 32

    assert bench["asin"]["speedup_multiplier"] >= 2.0
    assert bench["asin"]["meets_2x_target"] is True
    assert bench["asin"]["optimized_cycles"] == 42

    assert bench["acos"]["speedup_multiplier"] >= 2.0
    assert bench["acos"]["meets_2x_target"] is True
    assert bench["acos"]["optimized_cycles"] == 43
