"""Comprehensive unit tests for math_utils module.
Resolves Issue #976: [Bounty] Add fibonacci function with edge case handling.

Requirements:
- fibonacci(0) -> 0
- fibonacci(1) -> 1
- fibonacci(5) -> 5
- fibonacci(10) -> 55
- fibonacci(-1) -> raises ValueError with message "n must be non-negative"
- Large N calculations and type validations
"""

import pytest
from src.math_utils import fibonacci


def test_fibonacci_base_cases():
    assert fibonacci(0) == 0
    assert fibonacci(1) == 1


def test_fibonacci_normal_cases():
    assert fibonacci(2) == 1
    assert fibonacci(3) == 2
    assert fibonacci(4) == 3
    assert fibonacci(5) == 5
    assert fibonacci(6) == 8
    assert fibonacci(7) == 13
    assert fibonacci(8) == 21
    assert fibonacci(9) == 34
    assert fibonacci(10) == 55


def test_fibonacci_large_n():
    assert fibonacci(20) == 6765
    assert fibonacci(30) == 832040


def test_fibonacci_negative_edge_case():
    with pytest.raises(ValueError, match="n must be non-negative"):
        fibonacci(-1)

    with pytest.raises(ValueError, match="n must be non-negative"):
        fibonacci(-42)


def test_fibonacci_invalid_types():
    with pytest.raises(TypeError, match="n must be an integer"):
        fibonacci(3.14)

    with pytest.raises(TypeError, match="n must be an integer"):
        fibonacci("5")

    with pytest.raises(TypeError, match="n must be an integer"):
        fibonacci(True)
