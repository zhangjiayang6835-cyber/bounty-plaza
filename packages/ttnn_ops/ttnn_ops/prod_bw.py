"""
Module for zero-safe product backward (prod_bw) operations.

Provides mathematically rigorous gradient computations for tensor product operations,
preventing non-finite gradients (NaN/Inf) when inputs contain exact zeros.
"""

from dataclasses import dataclass
from typing import Optional, Sequence, Union
import torch


@dataclass(frozen=True)
class _ReductionState:
    """Encapsulates intermediate reduction buffers."""
    zero_mask: torch.Tensor
    nz_input: torch.Tensor
    reciprocal_nz: torch.Tensor


def _align_gradient_dimensions(
    grad: torch.Tensor,
    input_dim: int,
    dims: Sequence[int],
    keepdim: bool,
) -> torch.Tensor:
    """
    Aligns upstream gradient dimensions to match input tensor dimensionality.

    Args:
        grad: Incoming gradient tensor.
        input_dim: Number of dimensions in input tensor.
        dims: Sequence of reduction dimensions.
        keepdim: Whether forward operation kept dimensions.

    Returns:
        Expanded gradient tensor with matching rank.
    """
    if keepdim:
        return grad
    aligned = grad
    for d in sorted(dims):
        norm_d = d if d >= 0 else d + input_dim
        aligned = aligned.unsqueeze(norm_d)
    return aligned


def _compute_prod_bw_all_dims(
    grad: torch.Tensor,
    input_tensor: torch.Tensor,
    state: _ReductionState,
) -> torch.Tensor:
    """Computes gradient for full reduction across all dimensions."""
    num_zeros = torch.sum(state.zero_mask)
    grad_prod = grad * torch.prod(state.nz_input)
    grad_0 = grad_prod * state.reciprocal_nz
    grad_1 = torch.where(state.zero_mask.bool(), grad_prod, torch.zeros_like(input_tensor))

    cond_0 = num_zeros == 0
    cond_1 = num_zeros == 1
    fallback = torch.zeros_like(input_tensor)
    return torch.where(cond_0, grad_0, torch.where(cond_1, grad_1, fallback))


def _compute_prod_bw_dims(
    grad: torch.Tensor,
    input_tensor: torch.Tensor,
    state: _ReductionState,
    dims: Sequence[int],
    keepdim: bool,
) -> torch.Tensor:
    """Computes gradient for reductions across specific dimensions."""
    num_zeros = state.zero_mask
    prod_nz = state.nz_input
    for d in sorted(dims, reverse=True):
        num_zeros = torch.sum(num_zeros, dim=d, keepdim=True)
        prod_nz = torch.prod(prod_nz, dim=d, keepdim=True)

    aligned_grad = _align_gradient_dimensions(grad, input_tensor.dim(), dims, keepdim)
    grad_prod = aligned_grad * prod_nz
    grad_0 = grad_prod * state.reciprocal_nz
    grad_1 = torch.where(state.zero_mask.bool(), grad_prod, torch.zeros_like(input_tensor))

    cond_0 = num_zeros == 0
    cond_1 = num_zeros == 1
    fallback = torch.zeros_like(input_tensor)
    return torch.where(cond_0, grad_0, torch.where(cond_1, grad_1, fallback))


def compute_prod_bw(
    grad: torch.Tensor,
    input_tensor: torch.Tensor,
    dim: Optional[Union[int, Sequence[int]]] = None,
    keepdim: bool = False,
) -> torch.Tensor:
    """
    Computes the backward gradient of torch.prod with respect to input_tensor.

    Correctly handles tensors containing zeros by calculating derivatives based on
    zero-occurrence counts per reduction slice:
    - 0 zeros: grad * prod(input) / input
    - 1 zero at position m: grad * prod_{j != m}(input_j) at position m, and 0 elsewhere
    - 2+ zeros: 0 everywhere

    Args:
        grad: Incoming gradient tensor from upstream operations.
        input_tensor: Forward input tensor.
        dim: Dimension or dimensions along which product was performed.
        keepdim: Whether the forward reduction retained reduced dimensions.

    Returns:
        Gradient tensor with identical shape and dtype to input_tensor.
    """
    if input_tensor.numel() == 0:
        return torch.zeros_like(input_tensor)

    zero_mask = (input_tensor == 0.0).to(dtype=input_tensor.dtype)
    nz_input = torch.where(zero_mask.bool(), torch.ones_like(input_tensor), input_tensor)
    reciprocal_nz = torch.reciprocal(nz_input)
    state = _ReductionState(zero_mask, nz_input, reciprocal_nz)

    if dim is None:
        return _compute_prod_bw_all_dims(grad, input_tensor, state)

    dims = (dim,) if isinstance(dim, int) else tuple(dim)
    return _compute_prod_bw_dims(grad, input_tensor, state, dims, keepdim)


def compute_prod_bw_prefix_suffix(
    grad: torch.Tensor,
    input_tensor: torch.Tensor,
    dim: int = -1,
) -> torch.Tensor:
    """
    Alternative scan-based backward computation using prefix and suffix cumulative products.

    Computes partial derivatives without any division operations:
    d/dx_i (prod x) = (prefix_prod_{i-1}) * (suffix_prod_{i+1})

    Args:
        grad: Incoming gradient tensor.
        input_tensor: Forward input tensor.
        dim: Dimension along which product reduction was executed.

    Returns:
        Gradient tensor with respect to input_tensor.
    """
    dim_size = input_tensor.shape[dim]
    if dim_size == 1:
        return grad.expand_as(input_tensor)

    norm_dim = dim if dim >= 0 else dim + input_tensor.dim()

    prefix = torch.cumprod(input_tensor, dim=norm_dim)
    flipped = torch.flip(input_tensor, dims=[norm_dim])
    suffix = torch.flip(torch.cumprod(flipped, dim=norm_dim), dims=[norm_dim])

    ones_shape = list(input_tensor.shape)
    ones_shape[norm_dim] = 1
    ones_tensor = torch.ones(
        ones_shape, dtype=input_tensor.dtype, device=input_tensor.device
    )

    prefix_shifted = torch.cat(
        [ones_tensor, prefix.narrow(norm_dim, 0, dim_size - 1)], dim=norm_dim
    )
    suffix_shifted = torch.cat(
        [suffix.narrow(norm_dim, 1, dim_size - 1), ones_tensor], dim=norm_dim
    )

    excl_prod = prefix_shifted * suffix_shifted
    aligned_grad = grad if grad.dim() == input_tensor.dim() else grad.unsqueeze(norm_dim)
    return aligned_grad * excl_prod
