"""Math utility functions."""

from __future__ import annotations


def add(a: int | float, b: int | float) -> int | float:
    """Add two numbers.

    Parameters:
        a: First operand.
        b: Second operand.

    Returns:
        Sum of a and b.
    """
    return a + b


def multiply(a: int | float, b: int | float) -> int | float:
    """Multiply two numbers.

    Parameters:
        a: First operand.
        b: Second operand.

    Returns:
        Product of a and b.
    """
    return a * b


def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number (0-indexed).

    Parameters:
        n: Non-negative index of the Fibonacci number.

    Returns:
        The nth Fibonacci number.

    Raises:
        TypeError: If n is not an integer.
        ValueError: If n is negative.
    """
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an integer")
    if n < 0:
        raise ValueError("n must be non-negative")
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
