"""Canonical numerical kernels for ttnn quantization and requantization operations."""

import math
from typing import Any, Union
from packages.ttnn_quantize_saturation.types import DataType, RequantConfig


def _round_half_to_even(value: float) -> int:
    """Rounds a floating point value to the nearest integer with ties to even."""
    if math.isnan(value):
        return 0
    if math.isinf(value):
        return 255 if value > 0 else 0

    floor_val = math.floor(value)
    diff = value - floor_val

    if diff < 0.5:
        return int(floor_val)
    if diff > 0.5:
        return int(floor_val + 1)

    if floor_val % 2 == 0:
        return int(floor_val)
    return int(floor_val + 1)


def _clamp_to_dtype(value: int, dtype: DataType) -> int:
    """Clamps an integer value to the representable range of the target data type."""
    bounds = {
        DataType.UINT8: (0, 255),
        DataType.INT8: (-128, 127),
        DataType.INT32: (-2147483648, 2147483647),
    }
    min_bound, max_bound = bounds.get(dtype, (value, value))
    return max(min_bound, min(max_bound, value))


def _apply_elementwise(data: Any, func: Any) -> Any:
    """Recursively applies a transformation function across scalar or nested lists."""
    if isinstance(data, list):
        return [_apply_elementwise(element, func) for element in data]
    return func(data)


def quantize_element(
    val: float,
    scale: float,
    zero_point: int,
    dtype: DataType = DataType.UINT8
) -> int:
    """Quantizes a single floating point value with lower-bound saturation at zero."""
    if scale == 0.0:
        raise ValueError("Quantization scale cannot be zero.")

    scaled_val = val / scale + float(zero_point)

    if dtype == DataType.UINT8 and scaled_val < 0.0:
        return 0

    rounded = _round_half_to_even(scaled_val)
    return _clamp_to_dtype(rounded, dtype)


def requantize_element(
    val: Union[int, float],
    config: RequantConfig
) -> int:
    """Requantizes a single quantized value according to grid mapping configuration."""
    if config.in_scale == 0.0 or config.out_scale == 0.0:
        raise ValueError("Quantization scales must be non-zero.")

    unscaled = (float(val) - float(config.in_zero_point)) * config.in_scale
    scaled_output = (unscaled / config.out_scale) + float(config.out_zero_point)

    if config.dtype == DataType.UINT8 and scaled_output < 0.0:
        return 0

    rounded = _round_half_to_even(scaled_output)
    return _clamp_to_dtype(rounded, config.dtype)


def dequantize_element(
    val: int,
    scale: float,
    zero_point: int
) -> float:
    """Dequantizes an integer quantized value back into floating point space."""
    return (float(val) - float(zero_point)) * scale


def quantize(
    tensor: Any,
    scale: float,
    zero_point: int = 0,
    dtype: DataType = DataType.UINT8
) -> Any:
    """Quantizes a tensor elementwise into target data type with exact saturation."""
    def _op(x: float) -> int:
        return quantize_element(x, scale, zero_point, dtype)

    return _apply_elementwise(tensor, _op)


def _resolve_requant_config(args: tuple, kwargs: dict) -> RequantConfig:
    """Extracts and normalizes requantization configuration from arguments."""
    if len(args) == 1 and isinstance(args[0], RequantConfig):
        return args[0]
    if len(args) >= 4:
        in_scale = args[0]
        in_zp = args[1]
        out_scale = args[2]
        out_zp = args[3]
        target_dtype = args[4] if len(args) > 4 else kwargs.get("dtype", DataType.UINT8)
        return RequantConfig(in_scale, in_zp, out_scale, out_zp, target_dtype)

    in_scale = kwargs["in_scale"]
    in_zp = kwargs["in_zero_point"]
    out_scale = kwargs["out_scale"]
    out_zp = kwargs["out_zero_point"]
    target_dtype = kwargs.get("dtype", DataType.UINT8)
    return RequantConfig(in_scale, in_zp, out_scale, out_zp, target_dtype)


def requantize(tensor: Any, *args: Any, **kwargs: Any) -> Any:
    """Requantizes a tensor from source to target affine quantization parameters."""
    config = _resolve_requant_config(args, kwargs)

    def _op(x: Union[int, float]) -> int:
        return requantize_element(x, config)

    return _apply_elementwise(tensor, _op)


def dequantize(
    tensor: Any,
    scale: float,
    zero_point: int = 0
) -> Any:
    """Dequantizes a tensor back into float32 representation."""
    def _op(x: int) -> float:
        return dequantize_element(x, scale, zero_point)

    return _apply_elementwise(tensor, _op)


if __name__ == "__main__":
    test_input = [-10.0, -1.0, 0.0, 1.0, 10.0]
    quantized = quantize(test_input, scale=0.5, zero_point=10, dtype=DataType.UINT8)
    requantized = requantize(
        quantized,
        in_scale=0.5,
        in_zero_point=10,
        out_scale=1.0,
        out_zero_point=5,
        dtype=DataType.UINT8
    )
    dequantized = dequantize(requantized, scale=1.0, zero_point=5)
