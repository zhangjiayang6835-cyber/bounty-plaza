"""Mathematical utility functions.

Implements high-performance mathematical functions with strict input validation.
Resolves Issue #976: Add fibonacci function with edge case handling ($50 USD).
"""

from typing import Union


def fibonacci(n: int) -> int:
    """Calculates the nth Fibonacci number (0-indexed).

    Args:
        n (int): The non-negative index in the Fibonacci sequence.

    Returns:
        int: The nth Fibonacci number.

    Raises:
        ValueError: If n is negative, with message 'n must be non-negative'.
        TypeError: If n is not an integer.
    """
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError("n must be an integer")

    if n < 0:
        raise ValueError("n must be non-negative")

    if n == 0:
        return 0
    if n == 1:
        return 1

    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b

    return b
