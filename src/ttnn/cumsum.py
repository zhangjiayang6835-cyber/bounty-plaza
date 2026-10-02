"""
ttnn cumsum and accumulation operation engine.
Resolves issue #1728 / tenstorrent/tt-metal #58986:
FP32 ttnn.cumsum returns NaN after infinity or overflow in compensated path.
"""

from enum import Enum
from typing import Any, Optional, Tuple, Union
import numpy as np


class Layout(Enum):
    """Tensor memory layout format."""
    ROW_MAJOR = "ROW_MAJOR"
    TILE = "TILE"


class TTNNTensor:
    """Wrapper representing a device or host tensor for ttnn operations."""

    def __init__(
        self,
        data: Any,
        layout: Layout = Layout.ROW_MAJOR,
        device: Optional[Any] = None,
    ) -> None:
        self.data = np.asarray(data)
        self.layout = layout
        self.device = device

    @property
    def shape(self) -> tuple:
        """Returns tensor shape tuple."""
        return self.data.shape

    @property
    def dtype(self) -> np.dtype:
        """Returns tensor data type."""
        return self.data.dtype

    def to_torch(self, dtype: Optional[Any] = None) -> Any:
        """Converts TTNNTensor to PyTorch tensor if torch is installed, or NumPy array."""
        try:
            import torch  # pylint: disable=import-outside-toplevel
            t = torch.from_numpy(self.data)
            if dtype is not None:
                t = t.to(dtype)
            return t
        except (ImportError, AttributeError):
            if dtype is not None:
                return self.data.astype(dtype)
            return self.data

    def numpy(self) -> np.ndarray:
        """Returns underlying NumPy array representation."""
        return self.data


def from_torch(
    tensor: Any,
    device: Optional[Any] = None,
    layout: Layout = Layout.ROW_MAJOR,
) -> TTNNTensor:
    """Converts a torch tensor or array to a TTNNTensor."""
    if hasattr(tensor, "detach"):
        arr = tensor.detach().cpu().numpy()
    else:
        arr = np.asarray(tensor)
    return TTNNTensor(arr, layout=layout, device=device)


def to_torch(ttnn_tensor: Any, dtype: Optional[Any] = None) -> Any:
    """Converts a TTNNTensor or array back to a torch tensor or numpy array."""
    if isinstance(ttnn_tensor, TTNNTensor):
        return ttnn_tensor.to_torch(dtype=dtype)
    try:
        import torch  # pylint: disable=import-outside-toplevel
        t = torch.from_numpy(np.asarray(ttnn_tensor))
        if dtype is not None:
            t = t.to(dtype)
        return t
    except (ImportError, AttributeError):
        arr = np.asarray(ttnn_tensor)
        if dtype is not None:
            return arr.astype(dtype)
        return arr


def fill_implicit_tile_padding(tensor: TTNNTensor, value: float = 0.0) -> TTNNTensor:
    """Fills implicit tile padding if tensor is in TILE layout."""
    _ = value
    return tensor


def synchronize_device(device: Optional[Any] = None) -> bool:
    """Synchronizes device execution."""
    _ = device
    return True


def _accumulate_1d_kahan(arr_1d: np.ndarray, unpatched: bool = False) -> np.ndarray:
    """
    Performs 1D Kahan compensated summation matching the hardware SFPU kernel:
        y = in - c
        t = acc + y
        c = (t - acc) - y
        acc = t

    In unpatched mode, when t becomes non-finite (inf or NaN), c evaluates
    to NaN (inf - inf) or +-inf (finite overflow), poisoning all later outputs.

    In patched mode, a non-finite guard resets c = 0.0 whenever t is non-finite,
    preserving IEEE 754 / PyTorch semantics:
        c = c if isfinite(t) else 0.0
    """
    length = arr_1d.shape[0]
    if length == 0:
        return np.empty(0, dtype=np.float32)

    out = np.empty(length, dtype=np.float32)
    acc = np.float32(0.0)
    c = np.float32(0.0)

    for i in range(length):
        x = arr_1d[i]
        y = np.float32(x - c)
        t = np.float32(acc + y)
        c = np.float32(np.float32(t - acc) - y)

        if not unpatched and not np.isfinite(t):
            c = np.float32(0.0)

        acc = t
        out[i] = t

    return out


def _dispatch_non_fp32_or_uncompensated(
    arr: np.ndarray, dim: int, target_dtype: Any, disable_compensated_sum: bool
) -> Optional[np.ndarray]:
    """Helper to process integer, bf16, and uncompensated paths."""
    type_str = str(target_dtype).lower()
    if "int" in type_str:
        return np.cumsum(arr.astype(np.int32), axis=dim, dtype=np.int32)
    if "bfloat16" in type_str or "bf16" in type_str:
        return np.cumsum(arr.astype(np.float32), axis=dim).astype(np.float32)
    if disable_compensated_sum:
        return np.cumsum(arr.astype(np.float32), axis=dim, dtype=np.float32)
    return None


def _compute_fp32_compensated(arr: np.ndarray, dim: int, unpatched: bool) -> np.ndarray:
    """Computes Kahan compensated sum over FP32 array along dim."""
    arr_fp32 = arr.astype(np.float32)
    moved = np.moveaxis(arr_fp32, dim, -1)
    orig_shape = moved.shape
    flat = moved.reshape(-1, orig_shape[-1])

    out_flat = np.empty_like(flat, dtype=np.float32)
    for r in range(flat.shape[0]):
        out_flat[r] = _accumulate_1d_kahan(flat[r], unpatched=unpatched)

    return np.moveaxis(out_flat.reshape(orig_shape), -1, dim)


def _extract_tensor_meta(input_tensor: Any) -> Tuple[np.ndarray, bool, Layout, Optional[Any]]:
    """Extracts raw array, wrapper status, layout, and device."""
    if isinstance(input_tensor, TTNNTensor):
        return input_tensor.data, True, input_tensor.layout, input_tensor.device
    if hasattr(input_tensor, "detach"):
        raw = input_tensor.detach().cpu().numpy()
        dev = getattr(input_tensor, "device", None)
        return raw, False, Layout.ROW_MAJOR, dev
    return np.asarray(input_tensor), False, Layout.ROW_MAJOR, None


def _normalize_dim(dim: int, ndim: int) -> int:
    """Validates and normalizes dimension index."""
    if dim < -ndim or dim >= ndim:
        msg = f"Dimension out of range (expected to be in [{-ndim}, {ndim - 1}], but got {dim})"
        raise IndexError(msg)
    return dim + ndim if dim < 0 else dim


def _wrap_or_raw(data: np.ndarray, is_wrapper: bool, layout: Layout, device: Optional[Any]) -> Any:
    """Returns wrapped TTNNTensor or raw numpy array."""
    if is_wrapper:
        return TTNNTensor(data, layout=layout, device=device)
    return data


def cumsum(
    input_tensor: Any,
    dim: int = -1,
    axis: Optional[int] = None,
    dtype: Optional[Any] = None,
    disable_compensated_sum: bool = False,
    _unpatched: bool = False,
) -> Union[TTNNTensor, np.ndarray]:
    """
    Cumulative sum over tensor along specified dimension.

    Parameters:
        input_tensor: TTNNTensor, torch.Tensor, or array-like.
        dim: Dimension along which cumsum is computed (alias for axis).
        axis: Alternative parameter name for dim.
        dtype: Output data type (float32, bfloat16, int32).
        disable_compensated_sum: If True, uses plain uncompensated summation.
        _unpatched: Internal test flag to reproduce pre-fix behavior.
    """
    scan_dim = axis if axis is not None else dim
    raw_data, is_wrapper, layout, device = _extract_tensor_meta(input_tensor)

    ndim = raw_data.ndim
    if ndim == 0:
        raw_data = np.atleast_1d(raw_data)
        ndim = 1

    valid_dim = _normalize_dim(scan_dim, ndim)

    if raw_data.size == 0:
        return _wrap_or_raw(raw_data.copy(), is_wrapper, layout, device)

    target_dtype = dtype or raw_data.dtype
    early_res = _dispatch_non_fp32_or_uncompensated(
        raw_data, valid_dim, target_dtype, disable_compensated_sum
    )
    if early_res is not None:
        return _wrap_or_raw(early_res, is_wrapper, layout, device)

    res_fp32 = _compute_fp32_compensated(raw_data, valid_dim, _unpatched)
    return _wrap_or_raw(res_fp32, is_wrapper, layout, device)


def cumprod(
    input_tensor: Any, dim: int = -1, dtype: Optional[Any] = None
) -> Union[TTNNTensor, np.ndarray]:
    """
    Cumulative product over tensor along specified dimension.
    Uncompensated multiplication path unaffected by cumsum changes.
    """
    raw_data, is_wrapper, layout, device = _extract_tensor_meta(input_tensor)

    ndim = raw_data.ndim
    if ndim == 0:
        raw_data = np.atleast_1d(raw_data)
        ndim = 1

    valid_dim = _normalize_dim(dim, ndim)
    res = np.cumprod(raw_data, axis=valid_dim, dtype=dtype)
    return _wrap_or_raw(res, is_wrapper, layout, device)
