# SPDX-FileCopyrightText: © 2024-2026 Tenstorrent AI ULC
#
# SPDX-License-Identifier: Apache-2.0

import os
import sys
from pathlib import Path
import numpy as np

try:
    import pytest
except ImportError:
    class _MockMark:
        @staticmethod
        def parametrize(*args, **kwargs):
            def decorator(fn):
                return fn
            return decorator

        @staticmethod
        def skipif(*args, **kwargs):
            def decorator(fn):
                return fn
            return decorator

    class _MockPytest:
        mark = _MockMark()

    pytest = _MockPytest()

# Add src to path
src_dir = Path(__file__).resolve().parents[5] / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import ttnn

NON_FINITE_KINDS = [
    "pos_inf",               # [1, inf, 1, ...]      -> [1, inf, inf, ...]
    "neg_inf",               # [1, -inf, 1, ...]     -> [1, -inf, -inf, ...]
    "pos_overflow",          # [3e38, 3e38, 1, ...] -> [3e38, inf, inf, ...]
    "neg_overflow",          # [-3e38, -3e38, 1, ...] -> [-3e38, -inf, -inf, ...]
    "nan_input",             # [1, nan, 1, ...]     -> NaN from index 1 on
    "inf_last",              # [1, ..., 1, inf]     -> inf only at the end
    "pos_then_neg_inf",      # [1, inf, -inf, 1]    -> NaN from step 2 on
    "inf_then_large_neg",    # [inf, -1e32, ...]    -> stays +inf
    "neg_inf_then_large_pos",# [-inf, +1e32, ...]   -> stays -inf
]


def _non_finite_sequence(kind, n, dtype=np.float32):
    seq = np.ones(n, dtype=dtype)
    if kind == "pos_inf":
        seq[1] = np.inf
    elif kind == "neg_inf":
        seq[1] = -np.inf
    elif kind == "pos_overflow":
        seq[0] = 3e38
        seq[1] = 3e38
    elif kind == "neg_overflow":
        seq[0] = -3e38
        seq[1] = -3e38
    elif kind == "nan_input":
        seq[1] = np.nan
    elif kind == "inf_last":
        seq[-1] = np.inf
    elif kind == "pos_then_neg_inf":
        seq[1] = np.inf
        if n > 2:
            seq[2] = -np.inf
    elif kind == "inf_then_large_neg":
        seq[0] = np.inf
        seq[1] = -1e32
    elif kind == "neg_inf_then_large_pos":
        seq[0] = -np.inf
        seq[1] = 1e32
    return seq


def _scan_size(n, dim):
    return {0: [n, 4, 4], -2: [2, n, 4], -1: [2, 4, n]}[dim]


def _interleaved_scan_input(seq, size, dim, base):
    x = np.copy(base)
    moved = np.moveaxis(x, dim, -1)
    flat = moved.reshape(-1, moved.shape[-1])
    flat[0::2] = seq
    return np.moveaxis(flat.reshape(moved.shape), -1, dim)


def _assert_matches_expected_special_values(expected, actual):
    assert np.array_equal(np.isnan(actual), np.isnan(expected)), "NaN positions differ from expected"
    expected_inf = np.isinf(expected)
    assert np.array_equal(np.isinf(actual), expected_inf), "inf positions differ from expected"
    if np.any(expected_inf):
        assert np.array_equal(actual[expected_inf], expected[expected_inf]), "inf signs differ from expected"
    finite = np.isfinite(expected)
    if np.any(finite):
        np.testing.assert_allclose(actual[finite], expected[finite], rtol=1e-5, atol=1e-5)


@pytest.mark.parametrize("disable_compensated_sum", [False, True])
@pytest.mark.parametrize("kind", NON_FINITE_KINDS)
@pytest.mark.parametrize("dim", [0, -2, -1])
@pytest.mark.parametrize("n", [4, 8, 33])
def test_cumsum_fp32_non_finite_matches_expected(n, dim, kind, disable_compensated_sum):
    """
    Test that once running total is +-inf or NaN, FP32 cumsum preserves IEEE behavior.
    Covers +-inf inputs, finite overflow, NaN propagation, final element inf,
    on default compensated path and disable_compensated_sum=True.
    """
    size = _scan_size(n, dim)
    seq = _non_finite_sequence(kind, n, np.float32)
    base = np.random.randn(*size).astype(np.float32)
    inp = _interleaved_scan_input(seq, size, dim, base)

    tensor = ttnn.from_torch(inp, layout=ttnn.Layout.TILE)
    output_tensor = ttnn.cumsum(tensor, dim=dim, disable_compensated_sum=disable_compensated_sum)
    output = ttnn.to_torch(output_tensor)

    expected = np.cumsum(inp, axis=dim, dtype=np.float32)
    _assert_matches_expected_special_values(expected, output)


@pytest.mark.parametrize("kind", ["pos_inf", "neg_inf", "nan_input", "pos_then_neg_inf"])
@pytest.mark.parametrize("dim", [0, -2])
def test_cumsum_bf16_non_finite_unchanged(kind, dim):
    """BF16 never takes the compensated path; special-value behavior is unaffected."""
    n = 33
    size = _scan_size(n, dim)
    seq = _non_finite_sequence(kind, n, np.float32)
    base = np.random.randint(-2, 3, size=size).astype(np.float32)
    inp = _interleaved_scan_input(seq, size, dim, base)

    tensor = ttnn.from_torch(inp, layout=ttnn.Layout.TILE)
    output = ttnn.to_torch(ttnn.cumsum(tensor, dim=dim, dtype="bfloat16"))

    expected = np.cumsum(inp, axis=dim, dtype=np.float32)
    _assert_matches_expected_special_values(expected, output)


def run_all_tests():
    """Direct test runner executing all 170 parametrized combinations."""
    print("Running 170 parametrized reduce/cumsum unit tests...")
    count = 0
    for disable_comp in [False, True]:
        for kind in NON_FINITE_KINDS:
            for dim in [0, -2, -1]:
                for n in [4, 8, 33]:
                    test_cumsum_fp32_non_finite_matches_expected(n, dim, kind, disable_comp)
                    count += 1

    for kind in ["pos_inf", "neg_inf", "nan_input", "pos_then_neg_inf"]:
        for dim in [0, -2]:
            test_cumsum_bf16_non_finite_unchanged(kind, dim)
            count += 1

    print(f"Successfully passed all {count}/170 unit tests cleanly.")


if __name__ == "__main__":
    run_all_tests()
