# FILE: src/math_utils.py
"""Utility functions for mathematical operations.

This module currently contains a single function, :func:`fibonacci`, which
calculates the *n*th Fibonacci number (0‑indexed).  The implementation is
iterative to keep the time complexity linear and the memory usage constant.
"""

from __future__ import annotations

__all__ = ["fibonacci"]


def fibonacci(n: int) -> int:
    """Return the *n*th Fibonacci number.

    Parameters
    ----------
    n:
        The index of the Fibonacci sequence to return.  ``n`` must be a
        non‑negative integer.

    Returns
    -------
    int
        The *n*th Fibonacci number.

    Raises
    ------
    ValueError
        If ``n`` is negative.
    """

    if n < 0:
        raise ValueError("n must be non-negative")

    # Base cases
    if n == 0:
        return 0
    if n == 1:
        return 1

    # Iterative calculation – O(n) time, O(1) space
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b