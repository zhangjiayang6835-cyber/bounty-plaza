def fibonacci(n: int) -> int:
    """Return the nth Fibonacci number (0-indexed).

    Args:
        n: Non-negative integer index

    Returns:
        The nth Fibonacci number

    Raises:
        ValueError: If n is negative
    """
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