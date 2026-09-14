"""
Pytest test suite for Issue #973: ttnn.prod_bw zero-safe gradient computation.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import torch

from packages.ttnn_ops.ttnn_ops.prod_bw import (
    compute_prod_bw,
    compute_prod_bw_prefix_suffix,
)
from scripts.verify_issue_973 import (
    verify_cpp_implementation,
    verify_python_operator_module,
    run_full_verification,
)


def test_issue_973_reproducer_one_zero():
    """Verify exact issue reproducer [2.0, 0.0, 4.0] yields finite gradient [0.0, 8.0, 0.0]."""
    x = torch.tensor([2.0, 0.0, 4.0])
    grad = torch.tensor(1.0)
    expected = torch.tensor([0.0, 8.0, 0.0])

    actual = compute_prod_bw(grad, x, dim=None)
    assert torch.allclose(actual, expected)
    assert torch.isfinite(actual).all()


def test_prod_bw_no_zeros():
    """Verify standard gradient formula when input contains no zeros."""
    x = torch.tensor([2.0, 3.0, 4.0], requires_grad=True)
    y = torch.prod(x)
    grad = torch.tensor(2.0)
    y.backward(grad)
    expected = x.grad

    actual = compute_prod_bw(grad, x.detach(), dim=None)
    assert torch.allclose(actual, expected)
    assert torch.isfinite(actual).all()


def test_prod_bw_multiple_zeros():
    """Verify input with two or more zeros yields zero gradient everywhere."""
    x = torch.tensor([2.0, 0.0, 0.0, 4.0], requires_grad=True)
    y = torch.prod(x)
    grad = torch.tensor(1.0)
    y.backward(grad)
    expected = x.grad

    actual = compute_prod_bw(grad, x.detach(), dim=None)
    assert torch.allclose(actual, expected)
    assert torch.allclose(actual, torch.zeros_like(x))


def test_prod_bw_all_zeros():
    """Verify all-zero input returns all-zero gradient tensor."""
    x = torch.tensor([0.0, 0.0, 0.0], requires_grad=True)
    y = torch.prod(x)
    grad = torch.tensor(3.5)
    y.backward(grad)
    expected = x.grad

    actual = compute_prod_bw(grad, x.detach(), dim=None)
    assert torch.allclose(actual, expected)
    assert torch.allclose(actual, torch.zeros_like(x))


def test_prod_bw_single_element_and_empty():
    """Verify scalar-like single elements and empty tensor edge cases."""
    x_zero = torch.tensor([0.0], requires_grad=True)
    y_zero = torch.prod(x_zero)
    y_zero.backward()
    assert torch.allclose(compute_prod_bw(torch.tensor(1.0), x_zero.detach()), x_zero.grad)

    x_nonzero = torch.tensor([4.5], requires_grad=True)
    y_nonzero = torch.prod(x_nonzero)
    y_nonzero.backward()
    assert torch.allclose(compute_prod_bw(torch.tensor(1.0), x_nonzero.detach()), x_nonzero.grad)

    x_empty = torch.tensor([])
    actual_empty = compute_prod_bw(torch.tensor(1.0), x_empty)
    assert actual_empty.numel() == 0


def test_prod_bw_2d_per_dimension():
    """Verify 2D tensor reductions across both dimensions with keepdim True and False."""
    matrix = torch.tensor([
        [2.0, 0.0, 3.0],
        [0.0, 4.0, 0.0],
        [1.0, 2.0, 3.0],
    ])

    for dim in (0, 1, -1, -2):
        for keepdim in (True, False):
            x_ref = matrix.clone().detach().requires_grad_(True)
            y = torch.prod(x_ref, dim=dim, keepdim=keepdim)
            grad = torch.randn_like(y)
            y.backward(grad)
            expected = x_ref.grad

            actual = compute_prod_bw(grad, matrix, dim=dim, keepdim=keepdim)
            assert torch.allclose(actual, expected)
            assert torch.isfinite(actual).all()


def test_prod_bw_4d_per_dimension():
    """Verify 4D tensor reductions across all 4 dimensions matching TT-NN tile formats."""
    tensor_4d = torch.randn(2, 3, 4, 5)
    tensor_4d[0, 0, 0, 0] = 0.0
    tensor_4d[1, 2, 1, 3] = 0.0
    tensor_4d[1, 2, 1, 4] = 0.0

    for dim in range(4):
        for keepdim in (True, False):
            x_ref = tensor_4d.clone().detach().requires_grad_(True)
            y = torch.prod(x_ref, dim=dim, keepdim=keepdim)
            grad = torch.randn_like(y)
            y.backward(grad)
            expected = x_ref.grad

            actual = compute_prod_bw(grad, tensor_4d, dim=dim, keepdim=keepdim)
            assert torch.allclose(actual, expected, atol=1e-5)
            assert torch.isfinite(actual).all()


def test_prefix_suffix_scan_equivalence():
    """Verify scan-based prefix/suffix implementation produces identical results."""
    tensor = torch.tensor([
        [2.0, 0.0, 4.0],
        [3.0, 5.0, 1.0],
        [0.0, 0.0, 2.0],
    ])
    x_ref = tensor.clone().detach().requires_grad_(True)
    y = torch.prod(x_ref, dim=-1)
    grad = torch.tensor([1.0, 2.0, 3.0])
    y.backward(grad)
    expected = x_ref.grad

    actual = compute_prod_bw_prefix_suffix(grad, tensor, dim=-1)
    assert torch.allclose(actual, expected)
    assert torch.isfinite(actual).all()


def test_cpp_source_contract():
    """Verify C++ kernel implementation contains required zero-safe operations."""
    cpp_path = Path("packages/tt-metal/ttnn/cpp/ttnn/operations/eltwise/unary_backward/unary_backward.cpp")
    assert cpp_path.exists()
    assert verify_cpp_implementation(cpp_path.read_text(encoding="utf-8"))


def test_python_module_contract():
    """Verify Python operator module source contains required exports and symbols."""
    py_path = Path("packages/ttnn_ops/ttnn_ops/prod_bw.py")
    assert py_path.exists()
    assert verify_python_operator_module(py_path.read_text(encoding="utf-8"))


def test_end_to_end_verification_summary():
    """Verify overall verification routine passes 100% of checks."""
    summary = run_full_verification()
    assert summary.is_valid
    assert summary.passed_checks == summary.total_checks
    assert summary.total_checks == 6
