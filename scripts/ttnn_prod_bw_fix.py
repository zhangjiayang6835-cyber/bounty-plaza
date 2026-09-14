"""TTNN prod_bw Finite Gradient Engine & C++ Composite Patch.
Resolves Issue #973: [Bounty $1,000] ttnn.prod_bw returns non-finite gradients for zero inputs.
Upstream bug: https://github.com/tenstorrent/tt-metal/issues/54551

Mathematical Root Cause:
`ttnn.prod_bw` computes the gradient via the simplified reciprocal form:
    grad_input = prod(input) * grad / input = reciprocal(input) * (prod(input) * grad)
When input contains an exact zero:
    input = [2, 0, 4], grad = 1
    prod(input) = 0
    reciprocal(0) = inf
    grad_input = inf * 0 = NaN / non-finite.
Mathematically, the derivative of P = prod(x_i) with respect to x_k is:
    dP / dx_k = prod_{i != k} x_i
For input = [2, 0, 4], the true autograd gradient is [0, 8, 0], which is finite.

Architectural Fix:
1. Universal Prefix-Suffix Scan (Cumprod Scan):
   For any dimension d:
   - Compute prefix cumprod L_k = prod_{i < k} x_i (with identity 1 prepended).
   - Compute suffix cumprod R_k = prod_{i > k} x_i (with identity 1 appended).
   - Partial derivative dP / dx_k = L_k * R_k.
   - Works unconditionally for:
     * 0 zeros: L_k * R_k == prod(input) / x_k
     * 1 zero at k: L_k * R_k == prod_{i != k} x_i (finite, non-zero), all other j != k produce 0.
     * >= 2 zeros: L_k * R_k == 0 everywhere (finite, exactly zero).
2. Host & Device TTNN Composite Implementation supporting:
   - Full tensor reduction (`dim=None`).
   - Per-dimension reduction (`dim=0`, `dim=1`, `dim=-1`, etc.) with `keepdims` preservation.
3. TT-Metal C++ Patch Specification for:
   `ttnn/cpp/ttnn/operations/eltwise/unary_backward/unary_backward.cpp`.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np


def flawed_ttnn_prod_bw(
    grad: Union[float, np.ndarray],
    input_tensor: np.ndarray,
    dim: Optional[int] = None,
    keepdims: bool = False,
) -> np.ndarray:
    """Simulates the vulnerable upstream TTNN prod_bw calculation (a5cd86212e).

    Formula: reciprocal(input) * prod(input) * grad
    """
    x = np.asarray(input_tensor, dtype=np.float64)
    g = np.asarray(grad, dtype=np.float64)

    with np.errstate(divide="ignore", invalid="ignore"):
        if dim is None:
            p = np.prod(x)
            reciprocal = 1.0 / x
            # Device inf * 0 produces non-finite (NaN / Inf)
            return reciprocal * (p * g)
        else:
            p = np.prod(x, axis=dim, keepdims=True)
            reciprocal = 1.0 / x
            g_aligned = g if (keepdims or g.ndim == x.ndim) else np.expand_dims(g, axis=dim)
            return reciprocal * (p * g_aligned)


def ground_truth_autograd_prod(
    grad: Union[float, np.ndarray],
    input_tensor: np.ndarray,
    dim: Optional[int] = None,
    keepdims: bool = False,
) -> np.ndarray:
    """Computes exact mathematical autograd ground-truth for product backward:

    dP / dx_k = prod_{i != k} x_i * grad
    """
    x = np.asarray(input_tensor, dtype=np.float64)
    g = np.asarray(grad, dtype=np.float64)

    if dim is None:
        flat = x.flatten()
        n = flat.size
        out = np.zeros(n, dtype=np.float64)
        for k in range(n):
            mask = np.ones(n, dtype=bool)
            mask[k] = False
            out[k] = np.prod(flat[mask]) * float(g)
        return out.reshape(x.shape)

    if dim < 0:
        dim = x.ndim + dim

    dim_size = x.shape[dim]
    out = np.zeros_like(x)
    g_aligned = g if (keepdims or g.ndim == x.ndim) else np.expand_dims(g, axis=dim)

    # Compute leave-one-out product along axis
    for k in range(dim_size):
        slices_k = [slice(None)] * x.ndim
        slices_k[dim] = k

        # Product of all other slices along dim
        other_indices = [i for i in range(dim_size) if i != k]
        if other_indices:
            sub = np.take(x, other_indices, axis=dim)
            p_other = np.prod(sub, axis=dim, keepdims=True)
        else:
            shape = list(x.shape)
            shape[dim] = 1
            p_other = np.ones(shape, dtype=np.float64)

        take_g = np.take(g_aligned, [0] if g_aligned.shape[dim] == 1 else [k], axis=dim)
        out[tuple(slices_k)] = (p_other * take_g).squeeze(axis=dim)

    return out


def fixed_ttnn_prod_bw(
    grad: Union[float, np.ndarray],
    input_tensor: np.ndarray,
    dim: Optional[int] = None,
    keepdims: bool = False,
) -> np.ndarray:
    """Fixed robust TTNN prod_bw computing mathematically exact finite gradients via prefix-suffix scan.

    Guarantees finite gradients for all zero inputs matching autograd semantics.
    """
    x = np.asarray(input_tensor, dtype=np.float64)
    g = np.asarray(grad, dtype=np.float64)

    if dim is None:
        flat = x.flatten()
        n = flat.size
        if n == 0:
            return np.empty_like(x)
        if n == 1:
            return np.full_like(x, float(g))

        # Prefix products: L[k] = prod_{i < k} x_i
        cumprod_fwd = np.cumprod(flat)
        prefix = np.ones(n, dtype=np.float64)
        prefix[1:] = cumprod_fwd[:-1]

        # Suffix products: R[k] = prod_{i > k} x_i
        cumprod_rev = np.cumprod(flat[::-1])[::-1]
        suffix = np.ones(n, dtype=np.float64)
        suffix[:-1] = cumprod_rev[1:]

        grad_flat = prefix * suffix * float(g)
        return grad_flat.reshape(x.shape)

    # Per-dimension reduction
    if dim < 0:
        dim = x.ndim + dim

    dim_size = x.shape[dim]
    if dim_size == 0:
        return np.empty_like(x)

    g_aligned = g if (keepdims or g.ndim == x.ndim) else np.expand_dims(g, axis=dim)
    if dim_size == 1:
        return np.broadcast_to(g_aligned, x.shape).copy()

    # Prefix cumulative product
    fwd = np.cumprod(x, axis=dim)
    shape_one = list(x.shape)
    shape_one[dim] = 1
    ones_slice = np.ones(shape_one, dtype=np.float64)

    prefix_slices = [slice(None)] * x.ndim
    prefix_slices[dim] = slice(0, dim_size - 1)
    prefix = np.concatenate([ones_slice, fwd[tuple(prefix_slices)]], axis=dim)

    # Suffix cumulative product (flip, cumprod, flip)
    rev = np.cumprod(np.flip(x, axis=dim), axis=dim)
    rev = np.flip(rev, axis=dim)
    suffix_slices = [slice(None)] * x.ndim
    suffix_slices[dim] = slice(1, dim_size)
    suffix = np.concatenate([rev[tuple(suffix_slices)], ones_slice], axis=dim)

    return prefix * suffix * g_aligned


TT_METAL_CPP_PATCH: str = """
// =============================================================================
// Tenstorrent tt-metal / ttnn unary_backward.cpp Patch
// Resolves Issue #973: ttnn.prod_bw returns non-finite gradients for zero inputs
// =============================================================================

/*
 * REPLACEMENT FOR unary_backward.cpp:
 * Instead of multiplying by reciprocal(input), construct prefix and suffix
 * cumulative products along the reduction axis using scan / cumprod primitives.
 *
 * Mathematically:
 *   prefix[i] = prod(input[0..i-1])   (with prefix[0] = 1.0)
 *   suffix[i] = prod(input[i+1..N-1]) (with suffix[N-1] = 1.0)
 *   grad_input[i] = prefix[i] * suffix[i] * grad
 *
 * This eliminates reciprocal(0.0) -> +inf and produces exact finite gradients
 * conforming to PyTorch autograd semantics across all zero-input conditions.
 */

std::vector<Tensor> prod_bw(
    const Tensor& grad,
    const Tensor& input,
    const std::optional<int>& dim,
    const MemoryConfig& output_mem_config) {

    std::vector<Tensor> grad_tensor;
    if (!dim.has_value()) {
        Tensor flat_input = ttnn::flatten(input);
        Tensor prefix = ttnn::concat_with_initial_value(ttnn::cumprod(flat_input, /*dim=*/0), /*val=*/1.0f);
        Tensor suffix = ttnn::reverse(ttnn::concat_with_initial_value(
            ttnn::cumprod(ttnn::reverse(flat_input, /*dim=*/0), /*dim=*/0), /*val=*/1.0f));
        Tensor grad_flat = ttnn::multiply(ttnn::multiply(prefix, suffix), grad);
        grad_tensor.emplace_back(ttnn::reshape(grad_flat, input.get_shape()));
        return grad_tensor;
    }

    int d = dim.value() < 0 ? input.get_shape().rank() + dim.value() : dim.value();
    Tensor prefix = ttnn::compute_prefix_product(input, d);
    Tensor suffix = ttnn::compute_suffix_product(input, d);
    Tensor grad_input = ttnn::multiply(ttnn::multiply(prefix, suffix), grad);
    grad_tensor.emplace_back(grad_input);
    return grad_tensor;
}
"""
