"""Ledger boundary validator and checkpoint transition engine (#4245).

This module implements sequence verification, boundary transition mapping,
and checkpoint enforcement for distributed ledger event streaming.
"""

from __future__ import annotations

from typing import List, Tuple

DEFAULT_CHUNK_SIZE: int = 64


def compute_checkpoint_boundary(seq: int, chunk_size: int = DEFAULT_CHUNK_SIZE) -> int:
    """Compute the checkpoint boundary sequence for a given sequence number.

    A checkpoint boundary defines the inclusive upper boundary sequence of the
    synchronization epoch containing `seq`. For the default chunk size of 64:
      - seq in [0, 63]    -> boundary is 63
      - seq in [64, 127]  -> boundary is 127
      - seq in [128, 191] -> boundary is 191

    Mathematical invariants:
      compute_checkpoint_boundary(63) == 63
      compute_checkpoint_boundary(64) == 127
      compute_checkpoint_boundary(127) == 127

    Args:
        seq: Non-negative sequence integer.
        chunk_size: Positive integer denoting chunk interval (default: 64).

    Returns:
        The inclusive upper boundary sequence index for the epoch.

    Raises:
        ValueError: If seq is negative or chunk_size is non-positive.
    """
    if seq < 0:
        raise ValueError("Sequence number must be non-negative")
    if chunk_size <= 0:
        raise ValueError("Chunk size must be positive")

    return ((seq // chunk_size) + 1) * chunk_size - 1


class LedgerValidator:
    """Validator for ledger sequence numbers, transitions, and checkpoints."""

    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE, initial_sequence: int = 0) -> None:
        """Initialize LedgerValidator with chunk size and starting sequence.

        Args:
            chunk_size: Size of each checkpoint interval (must be > 0).
            initial_sequence: Sequence index to start from (must be >= 0).
        """
        if chunk_size <= 0:
            raise ValueError("Chunk size must be positive")
        if initial_sequence < 0:
            raise ValueError("Initial sequence must be non-negative")

        self.chunk_size = chunk_size
        self.current_sequence = initial_sequence
        self._checkpoints: List[int] = []

    def get_chunk_size(self) -> int:
        """Return the configured chunk size."""
        return self.chunk_size

    def get_current_sequence(self) -> int:
        """Return the current sequence index."""
        return self.current_sequence

    def compute_boundary(self, seq: int) -> int:
        """Compute checkpoint boundary using configured chunk size.

        Args:
            seq: Non-negative sequence number.

        Returns:
            Checkpoint boundary for the sequence.
        """
        return compute_checkpoint_boundary(seq, self.chunk_size)

    @staticmethod
    def compute_checkpoint_boundary(
        seq: int, chunk_size: int = DEFAULT_CHUNK_SIZE
    ) -> int:
        """Static helper to compute checkpoint boundary.

        Args:
            seq: Non-negative sequence number.
            chunk_size: Positive integer denoting chunk interval.

        Returns:
            Checkpoint boundary for the sequence.
        """
        return compute_checkpoint_boundary(seq, chunk_size)

    def is_checkpoint(self, seq: int) -> bool:
        """Determine whether seq is an exact checkpoint boundary.

        Args:
            seq: Sequence number to test.

        Returns:
            True if seq aligns with checkpoint boundary, False otherwise.
        """
        if seq < 0:
            return False
        return seq == self.compute_boundary(seq)

    def validate_sequence(self, current_seq: int, next_seq: int) -> bool:
        """Validate sequential progression from current_seq to next_seq.

        Args:
            current_seq: Preceding sequence number.
            next_seq: Succeeding sequence number.

        Returns:
            True if sequence strictly increments by 1, False otherwise.
        """
        if current_seq < 0 or next_seq < 0:
            return False
        return next_seq == current_seq + 1

    def step(self, next_seq: int) -> bool:
        """Advance validator state to next_seq if sequential transition is valid.

        Args:
            next_seq: Candidate next sequence number.

        Returns:
            True if state was successfully advanced, False otherwise.
        """
        if not self.validate_sequence(self.current_sequence, next_seq):
            return False
        self.current_sequence = next_seq
        if self.is_checkpoint(next_seq):
            self._checkpoints.append(next_seq)
        return True

    def recorded_checkpoints(self) -> List[int]:
        """Return a copy of all recorded checkpoint boundary sequences."""
        return list(self._checkpoints)

    def validate_batch(self, sequences: List[int]) -> bool:
        """Validate that a batch of sequences is strictly sequential.

        Args:
            sequences: List of candidate sequence numbers.

        Returns:
            True if batch is strictly monotonically increasing by 1.
        """
        if not sequences:
            return True
        for i in range(len(sequences) - 1):
            if not self.validate_sequence(sequences[i], sequences[i + 1]):
                return False
        return True

    def validate_block_range(self, start_seq: int, end_seq: int) -> Tuple[bool, int]:
        """Validate a contiguous block range and calculate required checkpoints.

        Args:
            start_seq: Inclusive starting sequence index.
            end_seq: Inclusive ending sequence index.

        Returns:
            Tuple of (is_valid, count_of_enclosed_checkpoints).
        """
        if start_seq < 0 or end_seq < start_seq:
            return False, 0

        first_cp = self.compute_boundary(start_seq)
        count = 0
        current_cp = first_cp
        while current_cp <= end_seq:
            count += 1
            current_cp += self.chunk_size

        return True, count
