"""Mathematical utility functions for bounty solver algorithms.
"""

def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number (0-indexed).

    Args:
        n (int): The index in the Fibonacci sequence.

    Returns:
        int: The nth Fibonacci number.

    Raises:
        ValueError: If n is negative with message 'n must be non-negative'.
        TypeError: If n is not an integer.
    """
    if not isinstance(n, int):
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
