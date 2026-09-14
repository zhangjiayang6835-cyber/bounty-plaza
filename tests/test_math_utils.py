"""Unit tests for math_utils module."""

import pytest

try:
    from src.math_utils import add, fibonacci, multiply
except ImportError:
    from math_utils import add, fibonacci, multiply


def test_add() -> None:
    """Verify addition operations with positive, negative, and zero operands."""
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0


def test_multiply() -> None:
    """Verify multiplication operations with positive, negative, and zero operands."""
    assert multiply(2, 3) == 6
    assert multiply(-1, 5) == -5
    assert multiply(0, 10) == 0


def test_fibonacci_base_cases() -> None:
    """Verify base cases for fibonacci calculation at indices 0 and 1."""
    assert fibonacci(0) == 0
    assert fibonacci(1) == 1


def test_fibonacci_normal_cases() -> None:
    """Verify fibonacci sequence values for typical positive integers."""
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


def test_fibonacci_negative_edge_cases() -> None:
    """Verify negative integers raise ValueError with the exact required error message."""
    with pytest.raises(ValueError, match="^n must be non-negative$"):
        fibonacci(-1)

    with pytest.raises(ValueError, match="^n must be non-negative$"):
        fibonacci(-10)

    with pytest.raises(ValueError, match="^n must be non-negative$"):
        fibonacci(-100)


def test_fibonacci_invalid_types() -> None:
    """Verify non-integer inputs raise TypeError."""
    with pytest.raises(TypeError, match="n must be an integer"):
        fibonacci("5")

    with pytest.raises(TypeError, match="n must be an integer"):
        fibonacci(True)

    with pytest.raises(TypeError, match="n must be an integer"):
        fibonacci(3.14)
