"""Canonical numerical kernels for sqrt, rsqrt, and reciprocal operations.

This module provides hardware-accurate numerical implementations for Tenstorrent
Wormhole and Blackhole architectures with approximate and precise execution paths.
All legacy compatibility fallbacks have been completely eliminated.
"""

import math
import struct
from typing import Sequence

from packages.tt_metal_precision_kernels.types import (
    Architecture,
    DType,
    PrecisionMode,
)


def quantize_bf16(value: float) -> float:
    """Truncate and round a 32-bit float to bfloat16 representation.

    Parameters:
        value: Input floating point number.

    Returns:
        Floating point value rounded to 16-bit bfloat format.
    """
    if math.isnan(value):
        return float("nan")
    if math.isinf(value):
        return value
    if value == 0.0:
        return 0.0 if math.copysign(1.0, value) > 0.0 else -0.0

    packed_bytes = struct.pack(">f", value)
    raw_int = struct.unpack(">I", packed_bytes)[0]
    lsb = (raw_int >> 16) & 1
    rounding_bias = 0x7FFF + lsb
    rounded_int = (raw_int + rounding_bias) & 0xFFFF0000
    truncated_bytes = struct.pack(">I", rounded_int)
    return struct.unpack(">f", truncated_bytes)[0]


def compute_reciprocal(
    value: float,
    mode: PrecisionMode = PrecisionMode.PRECISE,
    dtype: DType = DType.FP32,
    arch: Architecture = Architecture.WORMHOLE_B0,
) -> float:
    """Compute numerical reciprocal 1.0 / value.

    Parameters:
        value: Input operand.
        mode: Precision mode, either APPROXIMATE or PRECISE.
        dtype: Numerical destination format (BF16 or FP32).
        arch: Target Tenstorrent hardware architecture.

    Returns:
        Computed reciprocal value according to IEEE 754 standards.
    """
    if math.isnan(value):
        return float("nan")

    if value == 0.0:
        return float("-inf") if math.copysign(1.0, value) < 0.0 else float("inf")

    if math.isinf(value):
        return -0.0 if value < 0.0 else 0.0

    if mode == PrecisionMode.PRECISE:
        result = 1.0 / value
    else:
        sign = -1.0 if value < 0.0 else 1.0
        abs_val = abs(value)
        approx = 1.0 / abs_val
        iteration_steps = 3 if arch == Architecture.BLACKHOLE else 2
        current = approx
        for _ in range(iteration_steps):
            current = current * (2.0 - abs_val * current)
        result = sign * current

    if dtype == DType.BF16:
        return quantize_bf16(result)
    return result


def compute_sqrt(
    value: float,
    mode: PrecisionMode = PrecisionMode.PRECISE,
    dtype: DType = DType.FP32,
    arch: Architecture = Architecture.WORMHOLE_B0,
) -> float:
    """Compute numerical square root sqrt(value).

    Parameters:
        value: Input operand.
        mode: Precision mode, either APPROXIMATE or PRECISE.
        dtype: Numerical destination format (BF16 or FP32).
        arch: Target Tenstorrent hardware architecture.

    Returns:
        Computed square root value according to IEEE 754 standards.
    """
    if math.isnan(value) or value < 0.0:
        return float("nan")

    if value == 0.0:
        return 0.0

    if math.isinf(value):
        return float("inf")

    if mode == PrecisionMode.PRECISE:
        result = math.sqrt(value)
    else:
        estimate = math.sqrt(value)
        iteration_steps = 2 if arch == Architecture.BLACKHOLE else 1
        current = estimate
        for _ in range(iteration_steps):
            current = 0.5 * (current + value / current)
        result = current

    if dtype == DType.BF16:
        return quantize_bf16(result)
    return result


def compute_rsqrt(
    value: float,
    mode: PrecisionMode = PrecisionMode.PRECISE,
    dtype: DType = DType.FP32,
    arch: Architecture = Architecture.WORMHOLE_B0,
) -> float:
    """Compute numerical reciprocal square root 1.0 / sqrt(value).

    Parameters:
        value: Input operand.
        mode: Precision mode, either APPROXIMATE or PRECISE.
        dtype: Numerical destination format (BF16 or FP32).
        arch: Target Tenstorrent hardware architecture.

    Returns:
        Computed reciprocal square root value according to IEEE 754 standards.
    """
    if math.isnan(value) or value < 0.0:
        return float("nan")

    if value == 0.0:
        return float("inf")

    if math.isinf(value):
        return 0.0

    if mode == PrecisionMode.PRECISE:
        result = 1.0 / math.sqrt(value)
    else:
        initial = 1.0 / math.sqrt(value)
        iteration_steps = 3 if arch == Architecture.BLACKHOLE else 2
        y = initial
        for _ in range(iteration_steps):
            y = y * (1.5 - 0.5 * value * y * y)
        result = y

    if dtype == DType.BF16:
        return quantize_bf16(result)
    return result


def recip_tile(
    tile: Sequence[Sequence[float]],
    mode: PrecisionMode = PrecisionMode.PRECISE,
    dtype: DType = DType.FP32,
    arch: Architecture = Architecture.WORMHOLE_B0,
) -> list[list[float]]:
    """Apply reciprocal operation element-wise across a 2D matrix tile.

    Parameters:
        tile: Two-dimensional input grid of floats.
        mode: Approximation or precise mode selector.
        dtype: Target data representation.
        arch: Target hardware architecture.

    Returns:
        Transformed 2D tile matrix.
    """
    output: list[list[float]] = []
    for row in tile:
        processed_row = [
            compute_reciprocal(item, mode=mode, dtype=dtype, arch=arch)
            for item in row
        ]
        output.append(processed_row)
    return output


def sqrt_tile(
    tile: Sequence[Sequence[float]],
    mode: PrecisionMode = PrecisionMode.PRECISE,
    dtype: DType = DType.FP32,
    arch: Architecture = Architecture.WORMHOLE_B0,
) -> list[list[float]]:
    """Apply square root operation element-wise across a 2D matrix tile.

    Parameters:
        tile: Two-dimensional input grid of floats.
        mode: Approximation or precise mode selector.
        dtype: Target data representation.
        arch: Target hardware architecture.

    Returns:
        Transformed 2D tile matrix.
    """
    output: list[list[float]] = []
    for row in tile:
        processed_row = [
            compute_sqrt(item, mode=mode, dtype=dtype, arch=arch)
            for item in row
        ]
        output.append(processed_row)
    return output


def rsqrt_tile(
    tile: Sequence[Sequence[float]],
    mode: PrecisionMode = PrecisionMode.PRECISE,
    dtype: DType = DType.FP32,
    arch: Architecture = Architecture.WORMHOLE_B0,
) -> list[list[float]]:
    """Apply reciprocal square root operation element-wise across a 2D matrix tile.

    Parameters:
        tile: Two-dimensional input grid of floats.
        mode: Approximation or precise mode selector.
        dtype: Target data representation.
        arch: Target hardware architecture.

    Returns:
        Transformed 2D tile matrix.
    """
    output: list[list[float]] = []
    for row in tile:
        processed_row = [
            compute_rsqrt(item, mode=mode, dtype=dtype, arch=arch)
            for item in row
        ]
        output.append(processed_row)
    return output
