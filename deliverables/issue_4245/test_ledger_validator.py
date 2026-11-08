"""Comprehensive test suite for LedgerValidator boundary regression (#4245).

Asserts exact boundary transitions at seq=63 (63), seq=64 (127), and seq=127 (127)
per Boundary Transition Matrix specifications.
"""

from __future__ import annotations

import unittest
from typing import Dict, List

try:
    from deliverables.issue_4245.ledger_validator import (
        DEFAULT_CHUNK_SIZE,
        LedgerValidator,
        compute_checkpoint_boundary,
    )
except ImportError:
    try:
        from .ledger_validator import (  # type: ignore[no-redef]
            DEFAULT_CHUNK_SIZE,
            LedgerValidator,
            compute_checkpoint_boundary,
        )
    except ImportError:
        from ledger_validator import (  # type: ignore[no-redef]
            DEFAULT_CHUNK_SIZE,
            LedgerValidator,
            compute_checkpoint_boundary,
        )


class TestLedgerValidator(unittest.TestCase):
    """Unit and regression tests for LedgerValidator and boundary computations."""

    def test_checkpoint_boundary(self) -> None:
        """Assert exact boundary transitions at seq=63 (63), seq=64 (127), and seq=127 (127)."""
        # Primary regression requirements for Issue #4245
        self.assertEqual(compute_checkpoint_boundary(63), 63)
        self.assertEqual(compute_checkpoint_boundary(64), 127)
        self.assertEqual(compute_checkpoint_boundary(127), 127)

        # Instance-level computation verification
        validator = LedgerValidator(chunk_size=64)
        self.assertEqual(validator.compute_boundary(63), 63)
        self.assertEqual(validator.compute_boundary(64), 127)
        self.assertEqual(validator.compute_boundary(127), 127)

        # Static method verification
        self.assertEqual(LedgerValidator.compute_checkpoint_boundary(63), 63)
        self.assertEqual(LedgerValidator.compute_checkpoint_boundary(64), 127)
        self.assertEqual(LedgerValidator.compute_checkpoint_boundary(127), 127)

    def test_checkpoint_boundary_additional_points(self) -> None:
        """Verify boundary mapping across lower, intermediate, and upper sequence ranges."""
        self.assertEqual(compute_checkpoint_boundary(0), 63)
        self.assertEqual(compute_checkpoint_boundary(1), 63)
        self.assertEqual(compute_checkpoint_boundary(31), 63)
        self.assertEqual(compute_checkpoint_boundary(62), 63)
        self.assertEqual(compute_checkpoint_boundary(65), 127)
        self.assertEqual(compute_checkpoint_boundary(100), 127)
        self.assertEqual(compute_checkpoint_boundary(126), 127)
        self.assertEqual(compute_checkpoint_boundary(128), 191)
        self.assertEqual(compute_checkpoint_boundary(191), 191)
        self.assertEqual(compute_checkpoint_boundary(192), 255)

    def test_boundary_transition_matrix(self) -> None:
        """Verify the precise boundary transition around the 63 -> 64 inflection point."""
        transitions: Dict[int, int] = {
            60: 63,
            61: 63,
            62: 63,
            63: 63,
            64: 127,
            65: 127,
            66: 127,
        }
        for seq, expected_boundary in transitions.items():
            with self.subTest(seq=seq):
                self.assertEqual(compute_checkpoint_boundary(seq), expected_boundary)

    def test_is_checkpoint(self) -> None:
        """Verify detection of exact checkpoint boundaries."""
        validator = LedgerValidator(chunk_size=64)
        self.assertTrue(validator.is_checkpoint(63))
        self.assertFalse(validator.is_checkpoint(64))
        self.assertTrue(validator.is_checkpoint(127))
        self.assertFalse(validator.is_checkpoint(128))
        self.assertTrue(validator.is_checkpoint(191))
        self.assertFalse(validator.is_checkpoint(0))
        self.assertFalse(validator.is_checkpoint(-1))

    def test_invalid_inputs(self) -> None:
        """Verify ValueError is raised for negative sequences and invalid chunk sizes."""
        with self.assertRaises(ValueError):
            compute_checkpoint_boundary(-1)

        with self.assertRaises(ValueError):
            compute_checkpoint_boundary(10, chunk_size=0)

        with self.assertRaises(ValueError):
            compute_checkpoint_boundary(10, chunk_size=-10)

        with self.assertRaises(ValueError):
            LedgerValidator(chunk_size=0)

        with self.assertRaises(ValueError):
            LedgerValidator(initial_sequence=-5)

    def test_custom_chunk_sizes(self) -> None:
        """Verify boundary computation with non-default chunk sizes."""
        # 16-element chunks
        self.assertEqual(compute_checkpoint_boundary(15, chunk_size=16), 15)
        self.assertEqual(compute_checkpoint_boundary(16, chunk_size=16), 31)
        self.assertEqual(compute_checkpoint_boundary(31, chunk_size=16), 31)

        # 100-element chunks
        self.assertEqual(compute_checkpoint_boundary(0, chunk_size=100), 99)
        self.assertEqual(compute_checkpoint_boundary(99, chunk_size=100), 99)
        self.assertEqual(compute_checkpoint_boundary(100, chunk_size=100), 199)

    def test_validator_sequence_stepping(self) -> None:
        """Verify step progression and recording of checkpoint boundaries."""
        validator = LedgerValidator(chunk_size=64, initial_sequence=60)
        self.assertEqual(validator.get_current_sequence(), 60)
        self.assertEqual(validator.get_chunk_size(), 64)

        # Advance to 63
        self.assertTrue(validator.step(61))
        self.assertTrue(validator.step(62))
        self.assertTrue(validator.step(63))
        self.assertEqual(validator.recorded_checkpoints(), [63])

        # Advance to 65
        self.assertTrue(validator.step(64))
        self.assertTrue(validator.step(65))
        self.assertEqual(validator.recorded_checkpoints(), [63])

    def test_validator_invalid_transitions(self) -> None:
        """Verify that out-of-order, duplicate, or backwards steps are rejected."""
        validator = LedgerValidator(initial_sequence=10)
        # Skip sequence (10 -> 12)
        self.assertFalse(validator.step(12))
        # Duplicate sequence (10 -> 10)
        self.assertFalse(validator.step(10))
        # Backwards sequence (10 -> 9)
        self.assertFalse(validator.step(9))
        # Negative sequence
        self.assertFalse(validator.validate_sequence(-1, 0))
        self.assertFalse(validator.validate_sequence(0, -1))

    def test_validator_batch_processing(self) -> None:
        """Verify batch sequential validation."""
        validator = LedgerValidator()
        self.assertTrue(validator.validate_batch([]))
        self.assertTrue(validator.validate_batch([0]))
        self.assertTrue(validator.validate_batch([0, 1, 2, 3, 4]))
        self.assertFalse(validator.validate_batch([0, 1, 3, 4]))
        self.assertFalse(validator.validate_batch([2, 1]))

    def test_validator_block_range(self) -> None:
        """Verify block range validation and checkpoint tally."""
        validator = LedgerValidator(chunk_size=64)
        valid, count = validator.validate_block_range(0, 127)
        self.assertTrue(valid)
        self.assertEqual(count, 2)  # boundaries at 63 and 127

        valid, count = validator.validate_block_range(64, 127)
        self.assertTrue(valid)
        self.assertEqual(count, 1)  # boundary at 127

        valid, count = validator.validate_block_range(100, 50)
        self.assertFalse(valid)
        self.assertEqual(count, 0)

        valid, count = validator.validate_block_range(-1, 50)
        self.assertFalse(valid)
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
