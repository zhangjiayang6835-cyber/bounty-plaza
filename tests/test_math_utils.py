"""Comprehensive unit test suite for math_utils fibonacci implementation.
Resolves Issue #976: Add fibonacci function with edge case handling.
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


def test_fibonacci_edge_case_negative_input():
    with pytest.raises(ValueError) as exc_info:
        fibonacci(-1)
    assert "n must be non-negative" in str(exc_info.value)

    with pytest.raises(ValueError) as exc_info:
        fibonacci(-100)
    assert "n must be non-negative" in str(exc_info.value)


def test_fibonacci_type_validation():
    with pytest.raises(TypeError) as exc_info:
        fibonacci(3.14)  # type: ignore
    assert "n must be an integer" in str(exc_info.value)

    with pytest.raises(TypeError) as exc_info:
        fibonacci("5")  # type: ignore
    assert "n must be an integer" in str(exc_info.value)


def test_fibonacci_larger_values():
    assert fibonacci(20) == 6765
    assert fibonacci(30) == 832040
