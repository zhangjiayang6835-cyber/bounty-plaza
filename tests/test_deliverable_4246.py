"""Pytest discovery test suite for deliverable_4246 (#4246).

Validates:
- Strict rejection of boolean inputs (True/False) with TypeError("seq must be an exact int").
- Strict rejection of float inputs with TypeError("seq must be an exact int").
- Value range checking (seq >= 1).
- 64-ledger boundary calculations.
- Ledger header sequence continuity verification.
"""

from __future__ import annotations

import unittest
from typing import Any, Dict, List

from deliverable_4246 import (
    CANONICAL_GAP_CONTRACT,
    CHECKPOINT_INTERVAL,
    compute_checkpoint_boundary,
    verify_sequence_gap,
)


class TestDeliverable4246(unittest.TestCase):
    """Test suite for root deliverable_4246."""

    def test_checkpoint_boundary_exact_values(self) -> None:
        """Verify boundary calculation for exact valid integers."""
        self.assertEqual(compute_checkpoint_boundary(1), 63)
        self.assertEqual(compute_checkpoint_boundary(63), 63)
        self.assertEqual(compute_checkpoint_boundary(64), 127)
        self.assertEqual(compute_checkpoint_boundary(65), 127)
        self.assertEqual(compute_checkpoint_boundary(127), 127)
        self.assertEqual(compute_checkpoint_boundary(128), 191)
        self.assertEqual(compute_checkpoint_boundary(1000), 1023)
        self.assertEqual(compute_checkpoint_boundary(100_000), 100_031)

    def test_reject_bool_inputs(self) -> None:
        """Verify that booleans raise TypeError, not ValueError."""
        with self.assertRaises(TypeError) as ctx_true:
            compute_checkpoint_boundary(True)
        self.assertEqual(str(ctx_true.exception), "seq must be an exact int")

        with self.assertRaises(TypeError) as ctx_false:
            compute_checkpoint_boundary(False)
        self.assertEqual(str(ctx_false.exception), "seq must be an exact int")

    def test_reject_float_inputs(self) -> None:
        """Verify that floating point numbers raise TypeError before range check."""
        for val in [1.0, 64.0, 0.5, 0.0, -1.0, 1e5, float("inf"), float("nan")]:
            with self.subTest(val=val):
                with self.assertRaises(TypeError) as ctx:
                    compute_checkpoint_boundary(val)  # type: ignore[arg-type]
                self.assertEqual(str(ctx.exception), "seq must be an exact int")

    def test_reject_non_numeric_types(self) -> None:
        """Verify non-numeric types raise TypeError."""
        for val in ["1", "64", None, [1], (1,), {"seq": 1}, b"64", bytearray(b"64")]:
            with self.subTest(val=val):
                with self.assertRaises(TypeError) as ctx:
                    compute_checkpoint_boundary(val)  # type: ignore[arg-type]
                self.assertEqual(str(ctx.exception), "seq must be an exact int")

    def test_reject_non_positive_integers(self) -> None:
        """Verify that exact integers < 1 raise ValueError."""
        for val in [0, -1, -64, -1000]:
            with self.subTest(val=val):
                with self.assertRaises(ValueError) as ctx:
                    compute_checkpoint_boundary(val)
                self.assertEqual(str(ctx.exception), "sequence number must be >= 1")

    def test_sequence_continuity(self) -> None:
        """Verify sequence continuity checks."""
        self.assertTrue(verify_sequence_gap([]))
        self.assertTrue(verify_sequence_gap([{"seq": 1}]))
        self.assertTrue(verify_sequence_gap([{"seq": 10}, {"seq": 11}, {"seq": 12}]))
        headers: List[Dict[str, int]] = [{"seq": i} for i in range(100, 200)]
        self.assertTrue(verify_sequence_gap(headers))

        self.assertFalse(verify_sequence_gap([{"seq": 10}, {"seq": 12}]))
        self.assertFalse(verify_sequence_gap([{"seq": 10}, {"seq": 10}]))
        self.assertFalse(verify_sequence_gap([{"seq": 12}, {"seq": 11}]))

    def test_constants(self) -> None:
        """Verify exported constants."""
        self.assertEqual(CANONICAL_GAP_CONTRACT, "STRICT_CONTIGUOUS_STEP_1")
        self.assertEqual(CHECKPOINT_INTERVAL, 64)


if __name__ == "__main__":
    unittest.main()
