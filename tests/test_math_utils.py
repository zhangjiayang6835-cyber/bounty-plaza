"""Unit tests for mathematical utilities.

Resolves Issue #976: Add fibonacci function with edge case handling ($50 USD).
"""

import pytest
from src.math_utils import fibonacci


def test_fibonacci_base_cases():
    """Verifies that 0th and 1st Fibonacci numbers return 0 and 1 respectively."""
    assert fibonacci(0) == 0
    assert fibonacci(1) == 1


def test_fibonacci_standard_values():
    """Verifies standard Fibonacci sequence outputs."""
    assert fibonacci(2) == 1
    assert fibonacci(3) == 2
    assert fibonacci(4) == 3
    assert fibonacci(5) == 5
    assert fibonacci(6) == 8
    assert fibonacci(7) == 13
    assert fibonacci(8) == 21
    assert fibonacci(9) == 34
    assert fibonacci(10) == 55
    assert fibonacci(20) == 6765


def test_fibonacci_negative_edge_cases():
    """Verifies that negative inputs raise ValueError with 'n must be non-negative'."""
    with pytest.raises(ValueError, match=r"^n must be non-negative$"):
        fibonacci(-1)

    with pytest.raises(ValueError, match=r"^n must be non-negative$"):
        fibonacci(-10)

    with pytest.raises(ValueError, match=r"^n must be non-negative$"):
        fibonacci(-999)


def test_fibonacci_type_validation():
    """Verifies that non-integer inputs raise TypeError."""
    with pytest.raises(TypeError, match="n must be an integer"):
        fibonacci(3.14)  # type: ignore

    with pytest.raises(TypeError, match="n must be an integer"):
        fibonacci("5")  # type: ignore

    with pytest.raises(TypeError, match="n must be an integer"):
        fibonacci(True)  # type: ignore
