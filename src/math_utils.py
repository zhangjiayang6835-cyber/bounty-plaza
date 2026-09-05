# src/math_utils.py

def fibonacci(n: int) -> int:
    """Return the *n*th Fibonacci number (0‑indexed).

    Parameters
    ----------
    n: int
        Non‑negative integer index.

    Returns
    -------
    int
        The Fibonacci number at position *n*.

    Raises
    ------
    ValueError
        If *n* is negative.
    """
    if n < 0:
        raise ValueError("n must be non‑negative")
    if n == 0:
        return 0
    if n == 1:
        return 1
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b