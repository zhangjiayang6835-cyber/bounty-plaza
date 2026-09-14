"""Mathematical utilities module.
Provides mathematical helper algorithms including robust Fibonacci sequence calculation.
"""

from typing import Union


def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number (0-indexed).

    Args:
        n: The index of the Fibonacci number to compute (must be >= 0).

    Returns:
        The nth Fibonacci number.

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

    # Iterative O(N) computation with O(1) memory
    prev, curr = 0, 1
    for _ in range(2, n + 1):
        prev, curr = curr, prev + curr

    return curr
