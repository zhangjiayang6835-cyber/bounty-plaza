import numpy as np

def chebyshev_approximation(x, coeffs):
    """Compute the Chebyshev polynomial approximation."""
    T = [np.ones_like(x), x]
    for k in range(2, len(coeffs)):
        T_next = 2 * x * T[k-1] - T[k-2]
        T.append(T_next)
    return sum(c * t for c, t in zip(coeffs, T))

# Coefficients for the Chebyshev approximation of atan, asin, and acos
atan_coeffs = [0.0, 1.0, 0.0, -0.3333333333333333, 0.0, 0.2000000000000000, 0.0, -0.14285714285714285]
asin_coeffs = [0.0, 1.0, 0.0, 0.16666666666666666, 0.0, 0.07500000000000001, 0.0, 0.041666666666666664]
acos_coeffs = [np.pi / 2, -1.0, 0.0, -0.16666666666666666, 0.0, -0.07500000000000001, 0.0, -0.041666666666666664]

def fast_atan(x):
    """Fast atan using Chebyshev approximation."""
    return chebyshev_approximation(x, atan_coeffs)

def fast_asin(x):
    """Fast asin using Chebyshev approximation."""
    return chebyshev_approximation(x, asin_coeffs)

def fast_acos(x):
    """Fast acos using Chebyshev approximation."""
    return chebyshev_approximation(x, acos_coeffs)

# Example usage
if __name__ == "__main__":
    x = 0.5
    print(f"atan({x}) = {fast_atan(x)}")
    print(f"asin({x}) = {fast_asin(x)}")
    print(f"acos({x}) = {fast_acos(x)}")