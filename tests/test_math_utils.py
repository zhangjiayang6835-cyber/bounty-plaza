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
    with pytest.raises(ValueError) as excinfo:
        fibonacci(-1)
    assert str(excinfo.value) == "n must be non-negative"

    with pytest.raises(ValueError) as excinfo:
        fibonacci(-42)
    assert str(excinfo.value) == "n must be non-negative"

def test_fibonacci_invalid_type():
    with pytest.raises(TypeError):
        fibonacci(3.14)
    with pytest.raises(TypeError):
        fibonacci("5")
