"""Robust Gradient Calculation for ttnn.prod_bw with Zero Input Handling.
Resolves Issue #973: [Bounty $1,000] ttnn.prod_bw returns non-finite gradients for zero inputs.

Implements zero-masking gradient routing to eliminate non-finite (inf * 0 = NaN/inf)
evaluations in tt-metal composite backward reductions.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np


def ground_truth_prod_grad_nd(
    x: np.ndarray,
    grad_output: Optional[np.ndarray] = None,
    dim: Optional[int] = None,
    keepdim: bool = False,
) -> np.ndarray:
    """Computes exact analytical gradient of product reduction via element-wise leave-one-out."""
    x = np.asarray(x, dtype=np.float64)

    if dim is None:
        flat_x = x.ravel()
        n = len(flat_x)
        g_val = 1.0 if grad_output is None else float(np.asarray(grad_output).squeeze())
        grad_flat = np.zeros(n, dtype=np.float64)
        for i in range(n):
            p = 1.0
            for j in range(n):
                if j != i:
                    p *= flat_x[j]
            grad_flat[i] = g_val * p
        return grad_flat.reshape(x.shape)

    # Dimensional reduction
    norm_dim = dim % x.ndim
    axis_len = x.shape[norm_dim]
    grad_out = np.ones(
        [s for idx, s in enumerate(x.shape) if idx != norm_dim],
        dtype=np.float64,
    ) if grad_output is None else np.asarray(grad_output, dtype=np.float64)

    if keepdim and grad_out.ndim == x.ndim:
        grad_out = np.squeeze(grad_out, axis=norm_dim)

    grad = np.zeros_like(x, dtype=np.float64)
    # Move reduction axis to front for clean indexing
    x_trans = np.swapaxes(x, 0, norm_dim)
    grad_trans = np.swapaxes(grad, 0, norm_dim)

    for i in range(axis_len):
        # Product over all j != i
        other_indices = [j for j in range(axis_len) if j != i]
        if other_indices:
            p = np.prod(x_trans[other_indices], axis=0)
        else:
            p = np.ones_like(grad_out)
        grad_trans[i] = grad_out * p

    return np.swapaxes(grad_trans, 0, norm_dim)


def robust_prod_backward(
    input_tensor: Union[List[Any], np.ndarray],
    grad_output: Optional[Union[float, List[Any], np.ndarray]] = None,
    dim: Optional[int] = None,
    keepdim: bool = False,
) -> np.ndarray:
    """Zero-safe composite gradient computation for prod backward.

    Eliminates non-finite gradients by branching based on zero-occurrence counts:
    - zero_count == 0: grad * (prod(x) / x)
    - zero_count == 1: grad * prod_{k != i} x_k at zero position, 0 elsewhere
    - zero_count >= 2: all gradients are strictly 0.0

    Returns:
        np.ndarray: Finite analytical gradients matching autograd definition.
    """
    x = np.asarray(input_tensor, dtype=np.float64)
    zero_mask = (x == 0.0)

    # Case 1: Full reduction across all dimensions (dim=None)
    if dim is None:
        zero_count = int(np.sum(zero_mask))
        g = 1.0 if grad_output is None else float(np.asarray(grad_output).squeeze())

        if zero_count == 0:
            total_prod = float(np.prod(x))
            return g * (total_prod / x)

        if zero_count == 1:
            # Replace single zero with 1.0 to compute product of all non-zero elements
            safe_x = np.where(zero_mask, 1.0, x)
            non_zero_prod = float(np.prod(safe_x))
            grad = np.zeros_like(x, dtype=np.float64)
            grad[zero_mask] = g * non_zero_prod
            return grad

        # zero_count >= 2: Every single leave-one-out product retains at least one zero factor
        return np.zeros_like(x, dtype=np.float64)

    # Case 2: Per-dimension reduction
    norm_dim = dim % x.ndim
    zero_count_dim = np.sum(zero_mask, axis=norm_dim, keepdims=True)

    g_shape = list(x.shape)
    if grad_output is None:
        grad_expanded = np.ones(g_shape, dtype=np.float64)
    else:
        g_arr = np.asarray(grad_output, dtype=np.float64)
        if g_arr.ndim < x.ndim or g_arr.shape != x.shape:
            if not keepdim:
                g_arr = np.expand_dims(g_arr, axis=norm_dim)
            grad_expanded = np.broadcast_to(g_arr, x.shape)
        else:
            grad_expanded = g_arr

    # Safe x replaces 0 with 1 to evaluate products without zeroing out
    safe_x = np.where(zero_mask, 1.0, x)
    safe_prod = np.prod(safe_x, axis=norm_dim, keepdims=True)

    # Branch 0: No zeros along axis
    grad_no_zeros = grad_expanded * (safe_prod / safe_x)

    # Branch 1: Exactly 1 zero along axis -> Only zero element receives product of others
    grad_single_zero = np.where(zero_mask, grad_expanded * safe_prod, 0.0)

    # Combine branches based on zero_count
    result = np.where(
        zero_count_dim == 0,
        grad_no_zeros,
        np.where(zero_count_dim == 1, grad_single_zero, 0.0),
    )

    return result


CPP_UNARY_BACKWARD_PATCH: str = """
// =============================================================================
// C++ Source Fix for ttnn/cpp/ttnn/operations/eltwise/unary_backward/unary_backward.cpp
// Resolves: ttnn.prod_bw non-finite gradients for zero inputs (Issue #54551 / #973)
// =============================================================================

std::vector<Tensor> prod_bw(
    const Tensor& grad,
    const Tensor& input,
    const std::optional<int>& dim,
    const MemoryConfig& output_mem_config) {

    // 1. Detect zero inputs
    Tensor zero_mask = eq(input, 0.0f);

    if (!dim.has_value()) {
        // Full reduction: count total zeros in tensor
        Tensor zero_count = sum(zero_mask);
        Tensor safe_input = where(zero_mask, 1.0f, input);
        Tensor safe_prod = prod(safe_input);

        // Branch condition evaluation
        Tensor grad_no_zero = multiply(reciprocal(safe_input), fill_first_val_into_tensor(multiply(safe_prod, grad)));
        Tensor grad_one_zero = where(zero_mask, fill_first_val_into_tensor(multiply(safe_prod, grad)), 0.0f);

        Tensor result = where(
            eq(zero_count, 0.0f),
            grad_no_zero,
            where(eq(zero_count, 1.0f), grad_one_zero, zeros_like(input))
        );
        return {result};
    }

    // Per-dimension reduction
    int target_dim = dim.value();
    Tensor zero_count = sum(zero_mask, target_dim);
    Tensor safe_input = where(zero_mask, 1.0f, input);
    Tensor safe_prod = prod(safe_input, target_dim);

    Tensor grad_no_zero = multiply(reciprocal(safe_input), multiply(safe_prod, grad));
    Tensor grad_one_zero = where(zero_mask, multiply(safe_prod, grad), 0.0f);

    Tensor result = where(
        eq(zero_count, 0.0f),
        grad_no_zero,
        where(eq(zero_count, 1.0f), grad_one_zero, zeros_like(input))
    );
    return {result};
}
"""
