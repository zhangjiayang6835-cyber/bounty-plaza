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
    assert fibonacci(10) == 55
    assert fibonacci(20) == 6765


def test_fibonacci_negative_edge_case():
    with pytest.raises(ValueError, match="n must be non-negative"):
        fibonacci(-1)
    with pytest.raises(ValueError, match="n must be non-negative"):
        fibonacci(-100)


def test_fibonacci_type_validation():
    with pytest.raises(TypeError, match="n must be an integer"):
        fibonacci(3.14)  # type: ignore
    with pytest.raises(TypeError, match="n must be an integer"):
        fibonacci("5")  # type: ignore
    with pytest.raises(TypeError, match="n must be an integer"):
        fibonacci(True)  # type: ignore
