"""Unit tests for ledger checkpoint boundary and sequence continuity validator (#4246).

Validates:
- Exact 64-ledger boundary calculations.
- Rejection of bool (True/False) inputs with TypeError("seq must be an exact int").
- Rejection of float inputs with TypeError("seq must be an exact int") before range check.
- Rejection of other non-int inputs (str, None, list, dict) with TypeError.
- Rejection of non-positive sequence numbers (seq < 1) with ValueError.
- Verification of sequence continuity and gap detection.
"""

from __future__ import annotations

import unittest
from typing import Any, Dict, List

try:
    from deliverables.issue_4246.ledger_validator import (
        CANONICAL_GAP_CONTRACT,
        CHECKPOINT_INTERVAL,
        compute_checkpoint_boundary,
        verify_sequence_gap,
    )
except ImportError:
    try:
        from .ledger_validator import (  # type: ignore[no-redef]
            CANONICAL_GAP_CONTRACT,
            CHECKPOINT_INTERVAL,
            compute_checkpoint_boundary,
            verify_sequence_gap,
        )
    except ImportError:
        from ledger_validator import (  # type: ignore[no-redef]
            CANONICAL_GAP_CONTRACT,
            CHECKPOINT_INTERVAL,
            compute_checkpoint_boundary,
            verify_sequence_gap,
        )


class TestLedgerValidator4246(unittest.TestCase):
    """Test suite validating boundary calculations and strict type checking."""

    def test_checkpoint_boundary_exact_values(self) -> None:
        """Verify boundary computation for exact positive integer values."""
        self.assertEqual(compute_checkpoint_boundary(1), 63)
        self.assertEqual(compute_checkpoint_boundary(63), 63)
        self.assertEqual(compute_checkpoint_boundary(64), 127)
        self.assertEqual(compute_checkpoint_boundary(65), 127)
        self.assertEqual(compute_checkpoint_boundary(127), 127)
        self.assertEqual(compute_checkpoint_boundary(128), 191)
        self.assertEqual(compute_checkpoint_boundary(1000), 1023)
        self.assertEqual(compute_checkpoint_boundary(100_000), 100_031)

    def test_reject_bool_inputs(self) -> None:
        """Verify that booleans True and False raise TypeError, not ValueError."""
        with self.assertRaises(TypeError) as ctx_true:
            compute_checkpoint_boundary(True)
        self.assertEqual(str(ctx_true.exception), "seq must be an exact int")

        with self.assertRaises(TypeError) as ctx_false:
            compute_checkpoint_boundary(False)
        self.assertEqual(str(ctx_false.exception), "seq must be an exact int")

    def test_reject_float_inputs(self) -> None:
        """Verify that floating point inputs raise TypeError before checking seq < 1."""
        float_cases = [1.0, 64.0, 0.5, 0.0, -1.0, 1e5, float("inf"), float("nan")]
        for val in float_cases:
            with self.subTest(val=val):
                with self.assertRaises(TypeError) as ctx:
                    compute_checkpoint_boundary(val)  # type: ignore[arg-type]
                self.assertEqual(str(ctx.exception), "seq must be an exact int")

    def test_reject_non_numeric_types(self) -> None:
        """Verify that strings, None, lists, and dicts raise TypeError."""
        invalid_types: List[Any] = [
            "1",
            "64",
            None,
            [1],
            (1,),
            {"seq": 1},
            b"64",
            bytearray(b"64"),
        ]
        for val in invalid_types:
            with self.subTest(val=val):
                with self.assertRaises(TypeError) as ctx:
                    compute_checkpoint_boundary(val)  # type: ignore[arg-type]
                self.assertEqual(str(ctx.exception), "seq must be an exact int")

    def test_reject_non_positive_integers(self) -> None:
        """Verify that integers < 1 raise ValueError with expected message."""
        invalid_ints = [0, -1, -64, -1000]
        for val in invalid_ints:
            with self.subTest(val=val):
                with self.assertRaises(ValueError) as ctx:
                    compute_checkpoint_boundary(val)
                self.assertEqual(str(ctx.exception), "sequence number must be >= 1")

    def test_sequence_continuity_valid(self) -> None:
        """Verify contiguous sequence verification passes."""
        self.assertTrue(verify_sequence_gap([]))
        self.assertTrue(verify_sequence_gap([{"seq": 1}]))
        self.assertTrue(verify_sequence_gap([{"seq": 10}, {"seq": 11}, {"seq": 12}]))
        headers: List[Dict[str, int]] = [{"seq": i} for i in range(100, 200)]
        self.assertTrue(verify_sequence_gap(headers))

    def test_sequence_continuity_invalid_gaps(self) -> None:
        """Verify non-contiguous sequences or gaps return False."""
        self.assertFalse(verify_sequence_gap([{"seq": 10}, {"seq": 12}]))
        self.assertFalse(verify_sequence_gap([{"seq": 10}, {"seq": 10}]))
        self.assertFalse(verify_sequence_gap([{"seq": 12}, {"seq": 11}]))
        self.assertFalse(verify_sequence_gap([{"seq": 1}, {"seq": 3}, {"seq": 4}]))

    def test_contract_constants(self) -> None:
        """Verify canonical gap contract and checkpoint interval constants."""
        self.assertEqual(CANONICAL_GAP_CONTRACT, "STRICT_CONTIGUOUS_STEP_1")
        self.assertEqual(CHECKPOINT_INTERVAL, 64)


if __name__ == "__main__":
    unittest.main()
