"""
Tensor Unary Operations Optimization: deg2rad and rad2deg (fp32/bf16)
Optimized unary operation dispatch with high precision (PCC >= 0.9999).
"""

import numpy as np

DEG2RAD_FACTOR = np.float32(np.pi / 180.0)
RAD2DEG_FACTOR = np.float32(180.0 / np.pi)


def _to_bf16_numpy(arr: np.ndarray) -> np.ndarray:
    f32 = arr.astype(np.float32)
    u32 = f32.view(np.uint32)
    bf16_u32 = u32 & np.uint32(0xFFFF0000)
    return bf16_u32.view(np.float32)


def unary_dispatch(op: str, x: np.ndarray, dtype: str = "fp32") -> np.ndarray:
    if dtype == "bf16":
        x_processed = _to_bf16_numpy(x)
    else:
        x_processed = x.astype(np.float32, copy=False)

    if op == "deg2rad":
        result = x_processed * DEG2RAD_FACTOR
    elif op == "rad2deg":
        result = x_processed * RAD2DEG_FACTOR
    else:
        raise ValueError(f"Unsupported unary operation: {op}")

    if dtype == "bf16":
        return _to_bf16_numpy(result)
    return result


def deg2rad(x: np.ndarray, dtype: str = "fp32") -> np.ndarray:
    return unary_dispatch("deg2rad", x, dtype)


def rad2deg(x: np.ndarray, dtype: str = "fp32") -> np.ndarray:
    return unary_dispatch("rad2deg", x, dtype)
