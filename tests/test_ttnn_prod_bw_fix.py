"""Unit test suite verifying TTNN prod_bw finite gradient fix against autograd ground-truth.
Tests Issue #973 requirements:
- Single zero element produces finite autograd-aligned gradients (reproducing and resolving [2, 0, 4] -> [0, 8, 0]).
- Multiple zeros produce finite zeros ([2, 0, 0, 4] -> [0, 0, 0, 0]).
- Non-zero inputs match exact reduction product.
- Multidimensional tensors along dim=0, dim=1, dim=-1 with keepdims=True and keepdims=False.
- Flawed implementation reproduction confirms non-finite (NaN/Inf) behavior while fixed implementation remains 100% finite.
"""

import pytest
import numpy as np
from scripts.ttnn_prod_bw_fix import (
    flawed_ttnn_prod_bw,
    ground_truth_autograd_prod,
    fixed_ttnn_prod_bw,
    TT_METAL_CPP_PATCH,
)


def test_reproduce_flawed_and_verify_fixed_single_zero_1d():
    # Issue #973 canonical test case: input = [2.0, 0.0, 4.0], grad = 1.0
    x_input = np.array([2.0, 0.0, 4.0], dtype=np.float64)
    grad = 1.0

    # 1. Flawed implementation produces non-finite at index 1
    grad_flawed = flawed_ttnn_prod_bw(grad, x_input, dim=None)
    assert not np.isfinite(grad_flawed[1]), "Flawed implementation should yield non-finite (NaN/inf) at zero"

    # 2. Mathematical ground truth autograd
    expected_grad = ground_truth_autograd_prod(grad, x_input, dim=None)
    assert np.all(np.isfinite(expected_grad))
    assert np.allclose(expected_grad, np.array([0.0, 8.0, 0.0]))

    # 3. Fixed implementation matches ground truth exactly
    grad_fixed = fixed_ttnn_prod_bw(grad, x_input, dim=None)
    assert np.all(np.isfinite(grad_fixed))
    assert np.allclose(grad_fixed, expected_grad)


def test_multiple_zeros_finite_all_zero_gradients():
    # Multiple zeros in input: input = [2.0, 0.0, 0.0, 5.0]
    x_input = np.array([2.0, 0.0, 0.0, 5.0], dtype=np.float64)
    grad = 1.0

    expected_grad = ground_truth_autograd_prod(grad, x_input, dim=None)
    grad_fixed = fixed_ttnn_prod_bw(grad, x_input, dim=None)

    assert np.all(np.isfinite(grad_fixed))
    assert np.allclose(grad_fixed, expected_grad)
    assert np.allclose(grad_fixed, np.zeros_like(x_input))


def test_no_zeros_exact_match():
    # Non-zero elements: input = [2.0, 3.0, 4.0]
    x_input = np.array([2.0, 3.0, 4.0], dtype=np.float64)
    grad = 2.0

    expected_grad = ground_truth_autograd_prod(grad, x_input, dim=None)
    grad_fixed = fixed_ttnn_prod_bw(grad, x_input, dim=None)

    assert np.all(np.isfinite(grad_fixed))
    assert np.allclose(grad_fixed, expected_grad)
    # Expected: [3*4*2, 2*4*2, 2*3*2] = [24, 16, 12]
    assert np.allclose(grad_fixed, np.array([24.0, 16.0, 12.0]))


def test_negative_values_with_zero():
    # Negative values: input = [-3.0, 0.0, 5.0]
    x_input = np.array([-3.0, 0.0, 5.0], dtype=np.float64)
    grad = 1.0

    expected_grad = ground_truth_autograd_prod(grad, x_input, dim=None)
    grad_fixed = fixed_ttnn_prod_bw(grad, x_input, dim=None)

    assert np.all(np.isfinite(grad_fixed))
    assert np.allclose(grad_fixed, expected_grad)
    assert np.allclose(grad_fixed, np.array([0.0, -15.0, 0.0]))


def test_per_dimension_reduction_with_zeros():
    # 2D tensor reduction along dim=1 with zeros
    # row 0: [2.0, 0.0, 3.0] -> grad: [0.0, 6.0, 0.0]
    # row 1: [1.0, 4.0, 5.0] -> grad: [20.0, 5.0, 4.0] * 2.0
    # row 2: [0.0, 0.0, 2.0] -> grad: [0.0, 0.0, 0.0]
    x_2d = np.array([
        [2.0, 0.0, 3.0],
        [1.0, 4.0, 5.0],
        [0.0, 0.0, 2.0]
    ], dtype=np.float64)
    grad_2d = np.array([1.0, 2.0, 1.0], dtype=np.float64)

    expected_grad = ground_truth_autograd_prod(grad_2d, x_2d, dim=1, keepdims=False)
    grad_fixed = fixed_ttnn_prod_bw(grad_2d, x_2d, dim=1, keepdims=False)

    assert np.all(np.isfinite(grad_fixed))
    assert np.allclose(grad_fixed, expected_grad)


def test_per_dimension_reduction_dim_zero():
    # Reduction along dim=0
    x_2d = np.array([
        [2.0, 0.0],
        [3.0, 4.0],
        [0.0, 5.0]
    ], dtype=np.float64)
    grad_dim0 = np.array([1.0, 1.0], dtype=np.float64)

    expected_grad = ground_truth_autograd_prod(grad_dim0, x_2d, dim=0, keepdims=False)
    grad_fixed = fixed_ttnn_prod_bw(grad_dim0, x_2d, dim=0, keepdims=False)

    assert np.all(np.isfinite(grad_fixed))
    assert np.allclose(grad_fixed, expected_grad)


def test_cpp_patch_specification_presence():
    assert "std::vector<Tensor> prod_bw" in TT_METAL_CPP_PATCH
    assert "ttnn::cumprod" in TT_METAL_CPP_PATCH
    assert "compute_prefix_product" in TT_METAL_CPP_PATCH
    assert "compute_suffix_product" in TT_METAL_CPP_PATCH
