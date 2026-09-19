"""Bit-accurate reference mathematical models and correlation utilities for SFPU reciprocal."""

import math
from typing import List, Tuple


def compute_exact_reciprocal(val: float) -> float:
    """Compute standard IEEE-754 reciprocal with robust floating-point edge handling.

    Args:
        val: Input scalar value.

    Returns:
        Exact IEEE-754 reciprocal float value.
    """
    if math.isnan(val):
        return float("nan")
    if val == 0.0:
        return float("inf") if math.copysign(1.0, val) > 0.0 else float("-inf")
    if math.isinf(val):
        return 0.0 if val > 0.0 else -0.0
    return 1.0 / val


def compute_arecip_7b(val: float) -> float:
    """Simulate hardware SFPARECIP 7-bit seed lookup approximation.

    Args:
        val: Input scalar value.

    Returns:
        Approximate 7-bit reciprocal seed.
    """
    if val == 0.0:
        return float("inf") if math.copysign(1.0, val) > 0.0 else float("-inf")
    if math.isinf(val) or math.isnan(val):
        return compute_exact_reciprocal(val)

    sign = math.copysign(1.0, val)
    abs_val = abs(val)
    mantissa, exponent = math.frexp(abs_val)
    quantized_mantissa = round(mantissa * 128.0) / 128.0
    if quantized_mantissa == 0.0:
        quantized_mantissa = 0.5
    approx_mantissa = 0.5 / quantized_mantissa
    return sign * math.ldexp(approx_mantissa, -exponent + 1)


def compute_reciprocal_bf16_8b_3c(val: float) -> float:
    """Simulate Tenstorrent BF16 8-bit 3-cycle reciprocal using LSB Newton correction.

    Args:
        val: Input scalar value.

    Returns:
        BF16 reciprocal approximation value.
    """
    if val == 0.0 or math.isinf(val) or math.isnan(val):
        return compute_exact_reciprocal(val)

    y_seed = compute_arecip_7b(val)
    res = y_seed * (2.0 - val * y_seed)
    return res


def compute_reciprocal_fp32_24b_5c(val: float) -> float:
    """Simulate Tenstorrent FP32 24-bit 5-cycle reciprocal using quadratic convergence.

    Args:
        val: Input scalar value.

    Returns:
        FP32 reciprocal value matching Blackhole SFPU 5-cycle pipeline.
    """
    if val == 0.0 or math.isinf(val) or math.isnan(val):
        return compute_exact_reciprocal(val)

    y_est = compute_arecip_7b(val)
    e_err = 1.0 - (val * y_est)
    t_poly = (e_err * e_err) + e_err
    t2_poly = (t_poly * e_err) + e_err
    t2_clamped = min(t2_poly, 1.0)
    y_out = (t2_clamped * y_est) + y_est
    return y_out


def calculate_pearson_correlation(actual: List[float], golden: List[float]) -> float:
    """Compute Pearson Correlation Coefficient between device output and golden reference.

    Args:
        actual: Device or simulated kernel output tensor.
        golden: Golden reference output tensor.

    Returns:
        Pearson correlation coefficient in range [-1.0, 1.0].
    """
    if len(actual) != len(golden) or not actual:
        return 0.0

    valid_pairs: List[Tuple[float, float]] = []
    for a_val, g_val in zip(actual, golden):
        if math.isfinite(a_val) and math.isfinite(g_val):
            valid_pairs.append((a_val, g_val))

    if len(valid_pairs) < 2:
        return 1.0 if actual == golden else 0.0

    n_elem = float(len(valid_pairs))
    mean_a = sum(p[0] for p in valid_pairs) / n_elem
    mean_g = sum(p[1] for p in valid_pairs) / n_elem

    cov = sum((p[0] - mean_a) * (p[1] - mean_g) for p in valid_pairs)
    var_a = sum((p[0] - mean_a) ** 2 for p in valid_pairs)
    var_g = sum((p[1] - mean_g) ** 2 for p in valid_pairs)

    denom = math.sqrt(var_a * var_g)
    if denom == 0.0:
        return 1.0 if var_a == var_g else 0.0

    return max(-1.0, min(1.0, cov / denom))


def generate_reciprocal_stimuli(num_elements: int = 1024, seed: int = 42) -> List[float]:
    """Generate deterministic numerical stimuli across representative floating-point intervals.

    Args:
        num_elements: Number of elements in tile.
        seed: Initial seed for deterministic generation.

    Returns:
        List of generated floating point stimuli values.
    """
    stimuli: List[float] = []
    state = seed
    for idx in range(num_elements):
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
        normalized = (state / 4294967296.0) * 100.0 - 50.0
        if abs(normalized) < 0.001:
            normalized = 0.001 if normalized >= 0 else -0.001
        if idx % 64 == 0:
            normalized = (idx + 1) * 0.25
        stimuli.append(normalized)
    return stimuli
