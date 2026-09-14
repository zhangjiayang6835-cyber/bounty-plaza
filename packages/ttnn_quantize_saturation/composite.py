"""Composite operations and type narrowing for quantization workflows."""

from typing import Any
from packages.ttnn_quantize_saturation.types import DataType
from packages.ttnn_quantize_saturation.kernels import quantize


def is_narrow_quantized_dtype(dtype: DataType) -> bool:
    """Identifies whether the data type is a narrow quantized byte representation."""
    return dtype in (DataType.INT8, DataType.UINT8)


def typecast_wrapping(data: Any, dtype: DataType) -> Any:
    """Simulates modular hardware typecast without saturation clamping."""
    def _cast(val: float) -> int:
        int_val = int(val)
        if dtype == DataType.UINT8:
            return int_val & 0xFF
        if dtype == DataType.INT8:
            masked = int_val & 0xFF
            return masked - 256 if masked >= 128 else masked
        if dtype == DataType.INT32:
            masked = int_val & 0xFFFFFFFF
            return masked - 4294967296 if masked >= 2147483648 else masked
        return int_val

    if isinstance(data, list):
        return [typecast_wrapping(element, dtype) for element in data]
    return _cast(data)


def narrow_composite_result(
    shifted_tensor: Any,
    target_dtype: DataType
) -> Any:
    """Narrows composite floating point intermediate results into quantized target formats."""
    if not is_narrow_quantized_dtype(target_dtype):
        return typecast_wrapping(shifted_tensor, target_dtype)

    return quantize(
        tensor=shifted_tensor,
        scale=1.0,
        zero_point=0,
        dtype=target_dtype
    )
