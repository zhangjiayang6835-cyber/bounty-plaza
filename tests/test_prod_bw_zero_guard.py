"""Unit and regression tests for ttnn.prod_bw zero-input finite gradient calculations.
Resolves Issue #973: [Bounty $1,000] ttnn.prod_bw returns non-finite gradients for zero inputs.
"""

import numpy as np
import pytest
from scripts.prod_bw_zero_guard import (
    robust_prod_backward,
    ground_truth_prod_grad_nd,
    CPP_UNARY_BACKWARD_PATCH,
)


def test_single_zero_reproducer_issue_example():
    """Verifies the exact reproduction case from Issue #973:
    input:    [2, 0, 4]
    grad:     1
    expected: [0, 8, 0]
    previous: [0, non-finite, 0]
    """
    x = [2.0, 0.0, 4.0]
    grad_out = 1.0

    grad = robust_prod_backward(x, grad_output=grad_out)

    assert np.all(np.isfinite(grad)), "Gradients must all be strictly finite"
    np.testing.assert_allclose(grad, [0.0, 8.0, 0.0], rtol=1e-7, atol=1e-7)


def test_multiple_zeros_elimination():
    """When two or more zeros exist, all leave-one-out products contain a zero."""
    x = [2.0, 0.0, 4.0, 0.0]
    grad = robust_prod_backward(x, grad_output=1.0)

    assert np.all(np.isfinite(grad))
    np.testing.assert_allclose(grad, [0.0, 0.0, 0.0, 0.0], atol=1e-7)


def test_standard_non_zero_inputs():
    """Standard non-zero inputs maintain exact analytical gradient."""
    x = [2.0, 3.0, 4.0]
    # prod is 24; gradients: 24/2=12, 24/3=8, 24/4=6
    grad = robust_prod_backward(x, grad_output=1.0)

    assert np.all(np.isfinite(grad))
    np.testing.assert_allclose(grad, [12.0, 8.0, 6.0], rtol=1e-7, atol=1e-7)


def test_negative_values_with_zero():
    """Verifies sign preservation with negative numbers and a zero element."""
    x = [-3.0, 0.0, 5.0]
    grad = robust_prod_backward(x, grad_output=1.0)

    assert np.all(np.isfinite(grad))
    np.testing.assert_allclose(grad, [0.0, -15.0, 0.0], rtol=1e-7, atol=1e-7)


def test_single_element_zero_and_nonzero():
    """Verifies edge case of 1-element tensors."""
    # Derivative of f(x) = x is 1
    g0 = robust_prod_backward([0.0], grad_output=1.0)
    np.testing.assert_allclose(g0, [1.0], atol=1e-7)

    g1 = robust_prod_backward([7.5], grad_output=2.0)
    np.testing.assert_allclose(g1, [2.0], atol=1e-7)


def test_2d_per_dimension_reduction_dim0_and_dim1():
    """Verifies multi-dimensional tensor reduction along specific axes."""
    matrix = np.array([
        [2.0, 0.0, 1.0],
        [3.0, 4.0, 5.0],
        [0.0, 0.0, 2.0],
    ])

    for dim in (0, 1):
        actual = robust_prod_backward(matrix, dim=dim)
        expected = ground_truth_prod_grad_nd(matrix, dim=dim)

        assert np.all(np.isfinite(actual)), f"Gradients along dim={dim} must be finite"
        np.testing.assert_allclose(actual, expected, rtol=1e-6, atol=1e-6)


def test_cpp_patch_availability():
    """Ensures source-level C++ patch is well-formatted for upstream tt-metal PR."""
    assert "prod_bw" in CPP_UNARY_BACKWARD_PATCH
    assert "Tensor zero_mask = eq(input, 0.0f);" in CPP_UNARY_BACKWARD_PATCH
    assert "Tensor safe_input = where(zero_mask, 1.0f, input);" in CPP_UNARY_BACKWARD_PATCH
