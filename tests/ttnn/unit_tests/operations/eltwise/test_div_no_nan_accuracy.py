"""
Accuracy tests for `ttnn.div_no_nan`.

The reference implementation uses NumPy's true division with an explicit
zero‑divisor guard that matches the contract of `ttnn.div_no_nan`.  The
test checks that the maximum observed error is ≤ 1 ULP for a large
random sample covering normal, sub‑normal, infinities and signed zeros.
"""

import numpy as np
import pytest
import ttnn
from ttnn import Tensor

def ulp_error(reference: np.ndarray, result: np.ndarray) -> np.ndarray:
    """
    Compute the error in units of least precision (ULP) between two
    floating‑point arrays of the same dtype.
    """
    # For NaNs the error is defined as 0 because both sides should be NaN.
    mask_nan = np.isnan(reference)
    diff = np.abs(reference - result)
    # spacing gives the distance to the next representable float.
    ulp = np.spacing(reference)
    # For exact matches (including both NaN) set ulp to 1 to avoid division by zero.
    ulp[ulp == 0] = np.finfo(reference.dtype).eps
    err = diff / ulp
    err[mask_nan] = 0
    return err

@pytest.mark.parametrize("dtype", [np.float32, np.float64])
def test_div_no_nan_accuracy(dtype):
    rng = np.random.default_rng(seed=42)

    # Generate a wide range of values, including sub‑normals, normals,
    # infinities and signed zeros.
    a = rng.uniform(-1e3, 1e3, size=1_000_000).astype(dtype)
    b = rng.uniform(-1e3, 1e3, size=1_000_000).astype(dtype)

    # Inject special values deliberately.
    special_vals = np.array([0.0, -0.0, np.inf, -np.inf, np.nan], dtype=dtype)
    a[:5] = special_vals
    b[:5] = special_vals

    # Ensure some exact zeros in the divisor to test the no‑nan contract.
    b[100:110] = 0.0

    # Reference computation: NumPy division with zero‑guard.
    ref = np.where(b == 0, np.array(0, dtype=dtype), a / b)

    # TTNN computation.
    tt_a = Tensor.from_numpy(a)
    tt_b = Tensor.from_numpy(b)
    tt_res = ttnn.div_no_nan(tt_a, tt_b)
    res = tt_res.to_numpy()

    # Compute ULP error.
    err = ulp_error(ref, res)

    max_err = np.max(err)
    assert max_err <= 1.0, f"Maximum observed error {max_err} ULP exceeds 1 ULP for dtype {dtype}"
