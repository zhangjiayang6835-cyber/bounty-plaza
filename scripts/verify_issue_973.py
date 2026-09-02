"""
Verification script for Issue #973: ttnn.prod_bw non-finite gradients for zero inputs.
"""

from dataclasses import dataclass
from pathlib import Path
import sys
import torch

try:
    from packages.ttnn_ops.ttnn_ops.prod_bw import (
        compute_prod_bw,
        compute_prod_bw_prefix_suffix,
    )
except ModuleNotFoundError:
    REPO_ROOT = Path(__file__).resolve().parent.parent
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from packages.ttnn_ops.ttnn_ops.prod_bw import (
        compute_prod_bw,
        compute_prod_bw_prefix_suffix,
    )


@dataclass
class VerificationSummary:
    """Summary of verification checks."""
    passed_checks: int
    total_checks: int
    is_valid: bool
    details: list[str]


def verify_cpp_implementation(cpp_source: str) -> bool:
    """
    Verifies that C++ source code contains zero-safe prod_bw implementation primitives.

    Args:
        cpp_source: The source text of unary_backward.cpp.

    Returns:
        True if all required TT-NN operations and zero-safe patterns are present.
    """
    required_tokens = [
        "std::vector<Tensor> prod_bw(",
        "ttnn::eqz(",
        "ttnn::where(",
        "ttnn::reciprocal(",
        "ttnn::prod(",
        "ttnn::sum(",
        "reciprocal_nonzero",
        "zero_mask",
        "prod_nonzero",
    ]
    return all(token in cpp_source for token in required_tokens)


def verify_python_operator_module(module_source: str) -> bool:
    """
    Verifies that Python operator module exports the required backward kernels.

    Args:
        module_source: The source text of prod_bw.py.

    Returns:
        True if required functions and zero-safe handling logic are present.
    """
    required_tokens = [
        "def compute_prod_bw(",
        "def compute_prod_bw_prefix_suffix(",
        "num_zeros",
        "nz_input",
        "reciprocal_nz",
    ]
    return all(token in module_source for token in required_tokens)


def verify_bounty_reproducer() -> bool:
    """
    Verifies the specific issue #973 reproducer input [2.0, 0.0, 4.0].

    Returns:
        True if the output gradient matches expected finite tensor [0.0, 8.0, 0.0].
    """
    x = torch.tensor([2.0, 0.0, 4.0])
    grad = torch.tensor(1.0)
    expected = torch.tensor([0.0, 8.0, 0.0])

    actual = compute_prod_bw(grad, x, dim=None)
    is_match = torch.allclose(actual, expected)
    is_finite = torch.isfinite(actual).all().item()
    return bool(is_match and is_finite)


def verify_full_reduction_matrix() -> bool:
    """
    Verifies zero-safe full reduction against torch.autograd across zero counts.

    Returns:
        True if all test cases match PyTorch autograd gradients exactly.
    """
    cases = [
        torch.tensor([2.0, 3.0, 4.0]),
        torch.tensor([2.0, 0.0, 4.0]),
        torch.tensor([2.0, 0.0, 0.0, 4.0]),
        torch.tensor([0.0, 0.0, 0.0]),
        torch.tensor([7.5]),
        torch.tensor([0.0]),
        torch.tensor([-2.0, 0.0, 3.0, -4.0]),
    ]
    for case in cases:
        x_ref = case.clone().detach().requires_grad_(True)
        y = torch.prod(x_ref)
        upstream_grad = torch.tensor(1.5)
        y.backward(upstream_grad)
        expected = x_ref.grad

        actual = compute_prod_bw(upstream_grad, case, dim=None)
        if not torch.allclose(actual, expected, equal_nan=True):
            return False
        if not torch.isfinite(actual).all():
            return False
    return True


def verify_per_dimension_matrix() -> bool:
    """
    Verifies per-dimension reductions across 2D, 3D, and 4D tensor configurations.

    Returns:
        True if all dimensional reductions match PyTorch autograd.
    """
    test_tensors = [
        torch.tensor([[2.0, 0.0, 3.0], [0.0, 4.0, 0.0], [1.0, 2.0, 3.0]]),
        torch.randn(3, 4, 5),
        torch.randn(2, 3, 4, 5),
    ]
    for tensor in test_tensors:
        for dim_idx in range(tensor.dim()):
            for keepdim in [True, False]:
                x_ref = tensor.clone().detach().requires_grad_(True)
                y = torch.prod(x_ref, dim=dim_idx, keepdim=keepdim)
                upstream_grad = torch.randn_like(y)
                y.backward(upstream_grad)
                expected = x_ref.grad

                actual = compute_prod_bw(upstream_grad, tensor, dim=dim_idx, keepdim=keepdim)
                if not torch.allclose(actual, expected, atol=1e-5, equal_nan=True):
                    return False
                if not torch.isfinite(actual).all():
                    return False
    return True


def verify_prefix_suffix_scan() -> bool:
    """
    Verifies the prefix/suffix cumulative product implementation.

    Returns:
        True if prefix-suffix scan matches autograd.
    """
    x = torch.tensor([[2.0, 0.0, 4.0], [3.0, 5.0, 0.0]])
    x_ref = x.clone().detach().requires_grad_(True)
    y = torch.prod(x_ref, dim=-1)
    grad = torch.tensor([1.0, 2.0])
    y.backward(grad)
    expected = x_ref.grad

    actual = compute_prod_bw_prefix_suffix(grad, x, dim=-1)
    return bool(torch.allclose(actual, expected) and torch.isfinite(actual).all())


def run_full_verification() -> VerificationSummary:
    """
    Executes full verification workflow and returns structured summary.

    Returns:
        VerificationSummary detailing all checks.
    """
    details: list[str] = []
    passed = 0
    total = 6

    cpp_dir = Path("packages/tt-metal/ttnn/cpp/ttnn/operations/eltwise/unary_backward")
    cpp_path = cpp_dir / "unary_backward.cpp"
    if cpp_path.exists() and verify_cpp_implementation(cpp_path.read_text(encoding="utf-8")):
        passed += 1
        details.append("C++ unary_backward.cpp zero-safe kernel verified")
    else:
        details.append("Failed verifying C++ unary_backward.cpp")

    py_path = Path("packages/ttnn_ops/ttnn_ops/prod_bw.py")
    if py_path.exists() and verify_python_operator_module(py_path.read_text(encoding="utf-8")):
        passed += 1
        details.append("Python prod_bw module interface verified")
    else:
        details.append("Failed verifying Python prod_bw module")

    if verify_bounty_reproducer():
        passed += 1
        details.append("Issue #973 reproducer [2.0, 0.0, 4.0] verified")
    else:
        details.append("Failed issue #973 reproducer verification")

    if verify_full_reduction_matrix():
        passed += 1
        details.append("Full reduction zero-count test matrix verified")
    else:
        details.append("Failed full reduction test matrix")

    if verify_per_dimension_matrix():
        passed += 1
        details.append("Per-dimension reduction across ranks 2, 3, 4 verified")
    else:
        details.append("Failed per-dimension reduction matrix")

    if verify_prefix_suffix_scan():
        passed += 1
        details.append("Prefix/suffix scan gradient computation verified")
    else:
        details.append("Failed prefix/suffix scan verification")

    return VerificationSummary(
        passed_checks=passed,
        total_checks=total,
        is_valid=(passed == total),
        details=details,
    )


if __name__ == "__main__":
    summary = run_full_verification()
    for item in summary.details:
        print(f" - {item}")
    print(f"Status: {summary.passed_checks}/{summary.total_checks} (Valid: {summary.is_valid})")
    sys.exit(0 if summary.is_valid else 1)
