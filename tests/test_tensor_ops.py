"""
Unit tests for tensor_ops (deg2rad, rad2deg, fp32, bf16, PCC >= 0.9999)
"""

import numpy as np
import pytest
from tensor_ops import deg2rad, rad2deg, unary_dispatch


def compute_pcc(a: np.ndarray, b: np.ndarray) -> float:
    a_flat = a.flatten().astype(np.float64)
    b_flat = b.flatten().astype(np.float64)
    if np.all(a_flat == b_flat):
        return 1.0
    corr = np.corrcoef(a_flat, b_flat)[0, 1]
    return float(corr)


@pytest.mark.parametrize("dtype", ["fp32", "bf16"])
def test_deg2rad_rad2deg_roundtrip(dtype):
    x = np.linspace(-360, 360, 100, dtype=np.float32)
    rads = deg2rad(x, dtype=dtype)
    recons = rad2deg(rads, dtype=dtype)
    
    pcc = compute_pcc(x, recons)
    assert pcc >= 0.9999, f"PCC {pcc} below 0.9999 for dtype {dtype}"


def test_reference_values():
    x = np.array([0.0, 90.0, 180.0, 360.0], dtype=np.float32)
    expected_rad = x * (np.pi / 180.0)
    actual_rad = deg2rad(x, dtype="fp32")
    
    pcc = compute_pcc(expected_rad, actual_rad)
    assert pcc >= 0.9999
    np.testing.assert_allclose(actual_rad, expected_rad, rtol=1e-5, atol=1e-5)


def test_unary_dispatch_invalid():
    x = np.array([1.0, 2.0], dtype=np.float32)
    with pytest.raises(ValueError):
        unary_dispatch("invalid_op", x)
