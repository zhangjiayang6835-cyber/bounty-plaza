"""
Unit tests for FP32 ttnn.cumsum non-finite guard and compensated summation.
Resolves bounty issue #1728 / upstream tt-metal #58986:
'FP32 ttnn.cumsum returns NaN after infinity or overflow'
"""

import sys
import unittest
from pathlib import Path
import numpy as np

# Ensure src is in python path
repo_root = Path(__file__).resolve().parents[1]
src_dir = repo_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from ttnn import cumsum, cumprod, from_torch, to_torch, Layout


class TestTTNNCumsumIssue1728(unittest.TestCase):
    """
    Test suite verifying reproduction of failure before fix
    and 100% clean passing after the fix.
    """

    def setUp(self):
        np.random.seed(58986)

    def test_01_reproduce_failure_before_fix_inf(self):
        """
        Verify that the unpatched compensated path reproduces the bug:
        Input:    [1.0, inf, 1.0, 1.0]
        Output:   [1.0, inf, nan, nan]
        """
        inp = np.array([1.0, np.inf, 1.0, 1.0], dtype=np.float32)
        out_unpatched = cumsum(inp, _unpatched=True)

        self.assertAlmostEqual(out_unpatched[0], 1.0)
        self.assertTrue(np.isinf(out_unpatched[1]))
        self.assertTrue(np.isnan(out_unpatched[2]), "Expected NaN at index 2 in unpatched code")
        self.assertTrue(np.isnan(out_unpatched[3]), "Expected NaN at index 3 in unpatched code")

    def test_02_reproduce_failure_before_fix_overflow(self):
        """
        Verify that unpatched compensated summation fails on finite overflow:
        Input:    [3e38, 3e38, 1.0, 1.0]
        Output:   [3e38, inf, nan, nan]
        """
        inp = np.array([3e38, 3e38, 1.0, 1.0], dtype=np.float32)
        out_unpatched = cumsum(inp, _unpatched=True)

        self.assertAlmostEqual(out_unpatched[0], 3e38, delta=1e30)
        self.assertTrue(np.isinf(out_unpatched[1]))
        self.assertTrue(np.isnan(out_unpatched[2]), "Expected NaN after overflow in unpatched code")
        self.assertTrue(np.isnan(out_unpatched[3]), "Expected NaN after overflow in unpatched code")

    def test_03_reproduce_failure_before_fix_neg_inf(self):
        """
        Verify that unpatched compensated summation fails on -inf:
        Input:    [1.0, -inf, 1.0, 1.0]
        Output:   [1.0, -inf, nan, nan]
        """
        inp = np.array([1.0, -np.inf, 1.0, 1.0], dtype=np.float32)
        out_unpatched = cumsum(inp, _unpatched=True)

        self.assertAlmostEqual(out_unpatched[0], 1.0)
        self.assertTrue(np.isneginf(out_unpatched[1]))
        self.assertTrue(np.isnan(out_unpatched[2]))
        self.assertTrue(np.isnan(out_unpatched[3]))

    def test_04_fix_preserves_pytorch_pos_inf(self):
        """
        Verify that patched FP32 cumsum preserves IEEE/PyTorch behavior after +inf:
        Input:    [1.0, inf, 1.0, 1.0]
        Output:   [1.0, inf, inf, inf]
        """
        inp = np.array([1.0, np.inf, 1.0, 1.0], dtype=np.float32)
        out = cumsum(inp)

        self.assertEqual(out[0], 1.0)
        self.assertTrue(np.isposinf(out[1]))
        self.assertTrue(np.isposinf(out[2]))
        self.assertTrue(np.isposinf(out[3]))
        self.assertFalse(np.isnan(out).any())

    def test_05_fix_preserves_pytorch_neg_inf(self):
        """
        Verify that patched FP32 cumsum preserves IEEE/PyTorch behavior after -inf:
        Input:    [1.0, -inf, 1.0, 1.0]
        Output:   [1.0, -inf, -inf, -inf]
        """
        inp = np.array([1.0, -np.inf, 1.0, 1.0], dtype=np.float32)
        out = cumsum(inp)

        self.assertEqual(out[0], 1.0)
        self.assertTrue(np.isneginf(out[1]))
        self.assertTrue(np.isneginf(out[2]))
        self.assertTrue(np.isneginf(out[3]))
        self.assertFalse(np.isnan(out).any())

    def test_06_fix_handles_positive_overflow(self):
        """
        Verify that patched FP32 cumsum handles positive finite overflow:
        Input:    [3e38, 3e38, 1.0, 1.0]
        Output:   [3e38, inf, inf, inf]
        """
        inp = np.array([3e38, 3e38, 1.0, 1.0], dtype=np.float32)
        out = cumsum(inp)

        self.assertEqual(out[0], np.float32(3e38))
        self.assertTrue(np.isposinf(out[1]))
        self.assertTrue(np.isposinf(out[2]))
        self.assertTrue(np.isposinf(out[3]))
        self.assertFalse(np.isnan(out).any())

    def test_07_fix_handles_negative_overflow(self):
        """
        Verify that patched FP32 cumsum handles negative finite overflow:
        Input:    [-3e38, -3e38, 1.0, 1.0]
        Output:   [-3e38, -inf, -inf, -inf]
        """
        inp = np.array([-3e38, -3e38, 1.0, 1.0], dtype=np.float32)
        out = cumsum(inp)

        self.assertEqual(out[0], np.float32(-3e38))
        self.assertTrue(np.isneginf(out[1]))
        self.assertTrue(np.isneginf(out[2]))
        self.assertTrue(np.isneginf(out[3]))
        self.assertFalse(np.isnan(out).any())

    def test_08_scan_lengths_and_dimensions(self):
        """
        Verify across scan lengths 4, 8, 33 and dimensions 0, -2, -1:
        Both default compensated path and disable_compensated_sum=True.
        """
        for scan_len in [4, 8, 33]:
            for dim in [0, -2, -1]:
                shape = {0: (scan_len, 4, 4), -2: (2, scan_len, 4), -1: (2, 4, scan_len)}[dim]
                
                # Test positive infinity pattern
                arr = np.ones(shape, dtype=np.float32)
                idx = [slice(None)] * len(shape)
                idx[dim] = 1
                arr[tuple(idx)] = np.inf

                for disable_comp in [False, True]:
                    out = cumsum(arr, dim=dim, disable_compensated_sum=disable_comp)
                    expected = np.cumsum(arr, axis=dim, dtype=np.float32)
                    
                    self.assertTrue(np.array_equal(np.isnan(out), np.isnan(expected)))
                    self.assertTrue(np.array_equal(np.isinf(out), np.isinf(expected)))
                    self.assertTrue(np.array_equal(out[np.isinf(expected)], expected[np.isinf(expected)]))

    def test_09_nan_inputs_unchanged(self):
        """
        Verify unchanged behavior for NaN inputs:
        Input:    [1.0, nan, 1.0, 1.0]
        Output:   [1.0, nan, nan, nan]
        """
        inp = np.array([1.0, np.nan, 1.0, 1.0], dtype=np.float32)
        out = cumsum(inp)

        self.assertEqual(out[0], 1.0)
        self.assertTrue(np.isnan(out[1]))
        self.assertTrue(np.isnan(out[2]))
        self.assertTrue(np.isnan(out[3]))

    def test_10_infinity_at_final_scan_element(self):
        """
        Verify unchanged behavior when infinity appears at the final scan element:
        Input:    [1.0, 1.0, 1.0, inf]
        Output:   [1.0, 2.0, 3.0, inf]
        """
        inp = np.array([1.0, 1.0, 1.0, np.inf], dtype=np.float32)
        out = cumsum(inp)

        self.assertEqual(out[0], 1.0)
        self.assertEqual(out[1], 2.0)
        self.assertEqual(out[2], 3.0)
        self.assertTrue(np.isposinf(out[3]))

    def test_11_pos_inf_followed_by_neg_inf(self):
        """
        Verify +inf followed by -inf:
        Input:    [1.0, inf, -inf, 1.0]
        Output:   [1.0, inf, nan, nan] (since inf + (-inf) = NaN in IEEE 754)
        """
        inp = np.array([1.0, np.inf, -np.inf, 1.0], dtype=np.float32)
        out = cumsum(inp)

        self.assertEqual(out[0], 1.0)
        self.assertTrue(np.isposinf(out[1]))
        self.assertTrue(np.isnan(out[2]))
        self.assertTrue(np.isnan(out[3]))

    def test_12_finite_fp32_compensated_accuracy(self):
        """
        Verify finite FP32 inputs retain full Kahan compensated accuracy.
        Summing 1.0 + 100 * 1e-7 in FP32 loses precision with plain sum,
        while Kahan compensated sum preserves accuracy.
        """
        n = 100
        inp = np.array([1.0] + [1e-7] * n, dtype=np.float32)
        out_kahan = cumsum(inp, disable_compensated_sum=False)
        
        # Exact mathematical expected: 1.0 + n * 1e-7 = 1.0000100
        expected_math = 1.0 + float(n) * 1e-7
        self.assertAlmostEqual(out_kahan[-1], expected_math, delta=1e-6)

    def test_13_bf16_and_int32_cumsum_unaffected(self):
        """
        Verify BF16 and INT32 cumsum are unaffected and exact.
        """
        # INT32
        inp_int = np.array([10, 20, 30, 40], dtype=np.int32)
        out_int = cumsum(inp_int, dtype="int32")
        self.assertTrue(np.array_equal(out_int, np.array([10, 30, 60, 100], dtype=np.int32)))

        # BF16
        inp_bf16 = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
        out_bf16 = cumsum(inp_bf16, dtype="bfloat16")
        self.assertTrue(np.array_equal(out_bf16, np.array([1.0, 3.0, 6.0, 10.0], dtype=np.float32)))

    def test_14_cumprod_unaffected(self):
        """
        Verify FP32 cumprod operation is unaffected.
        """
        inp = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
        out = cumprod(inp)
        self.assertTrue(np.array_equal(out, np.array([1.0, 2.0, 6.0, 24.0], dtype=np.float32)))

    def test_15_interleaved_lanes_isolation(self):
        """
        Verify that adjacent lanes inside multidimensional tensors do not leak:
        Even lane contains +inf, odd lane contains purely finite numbers.
        """
        data = np.zeros((4, 8), dtype=np.float32)
        # Even rows have inf at col 1
        data[0::2, :] = 1.0
        data[0::2, 1] = np.inf
        # Odd rows have finite numbers
        data[1::2, :] = 2.0

        out = cumsum(data, dim=-1)

        # Check even rows: index 1 and beyond must be inf
        for r in range(0, 4, 2):
            self.assertEqual(out[r, 0], 1.0)
            for c in range(1, 8):
                self.assertTrue(np.isposinf(out[r, c]))

        # Check odd rows: must be exactly [2, 4, 6, 8, 10, 12, 14, 16]
        for r in range(1, 4, 2):
            expected_row = np.array([2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0], dtype=np.float32)
            self.assertTrue(np.array_equal(out[r], expected_row))

    def test_16_empty_tensor_and_zero_dimensions(self):
        """
        Verify robust handling of empty tensors and tensors with zero-sized dimensions.
        """
        empty_1d = np.array([], dtype=np.float32)
        out_empty = cumsum(empty_1d)
        self.assertEqual(out_empty.shape, (0,))

        zero_dim = np.zeros((2, 0, 4), dtype=np.float32)
        out_zero = cumsum(zero_dim, dim=1)
        self.assertEqual(out_zero.shape, (2, 0, 4))

        out_zero_last = cumsum(zero_dim, dim=-1)
        self.assertEqual(out_zero_last.shape, (2, 0, 4))

    def test_17_dimension_out_of_range(self):
        """
        Verify that out-of-range dimensions raise IndexError matching PyTorch behavior.
        """
        arr = np.ones((3, 4), dtype=np.float32)
        with self.assertRaises(IndexError):
            cumsum(arr, dim=5)
        with self.assertRaises(IndexError):
            cumsum(arr, dim=-3)
        with self.assertRaises(IndexError):
            cumprod(arr, dim=5)

    def test_18_scalar_input(self):
        """
        Verify that 0-D scalar inputs are correctly promoted and handled.
        """
        s = np.float32(7.5)
        out = cumsum(s)
        self.assertEqual(out.shape, (1,))
        self.assertEqual(out[0], np.float32(7.5))

    def test_19_subnormal_precision(self):
        """
        Verify that subnormal FP32 inputs accumulate without corrupting accumulator state.
        """
        subnormal = np.float32(1e-40)
        inp = np.array([subnormal, subnormal, 1.0], dtype=np.float32)
        out = cumsum(inp)
        self.assertAlmostEqual(out[-1], 1.0, places=5)

    def test_20_tensor_wrapper_roundtrip(self):
        """
        Verify TTNNTensor wrapper preserving metadata, layout, and device across cumsum.
        """
        arr = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        tensor = from_torch(arr, layout=Layout.TILE)
        out = cumsum(tensor, dim=0)
        self.assertEqual(out.layout, Layout.TILE)
        self.assertEqual(out.shape, (3,))
        torch_res = to_torch(out)
        self.assertEqual(len(torch_res), 3)


if __name__ == "__main__":
    unittest.main()

