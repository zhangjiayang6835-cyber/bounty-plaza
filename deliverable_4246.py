"""Ledger checkpoint boundary and sequence continuity validator (#4246).

This deliverable enforces strict type safety on `compute_checkpoint_boundary`, ensuring
exact integer semantics by rejecting booleans and floats before range verification.
"""

from __future__ import annotations

from typing import Any, Dict, Sequence, Union

CHECKPOINT_INTERVAL: int = 64
CANONICAL_GAP_CONTRACT: str = "STRICT_CONTIGUOUS_STEP_1"


def compute_checkpoint_boundary(seq: int) -> int:
    """Return the 64-ledger checkpoint boundary for a positive sequence number.

    A checkpoint boundary occurs every 64 ledgers (at sequence 63, 127, 191, ...).
    For any positive ledger sequence number `seq`, this function computes the
    closing sequence of the corresponding 64-ledger checkpoint window.

    Type Invariant:
        `seq` must be an exact integer. Boolean instances (True/False) and floating
        point numbers are rejected before checking if `seq < 1`.

    Args:
        seq: Positive ledger sequence number (exact int >= 1).

    Returns:
        The closing sequence number of the corresponding 64-ledger checkpoint boundary.

    Raises:
        TypeError: If `seq` is a boolean, float, or any non-int type.
        ValueError: If `seq` is an integer strictly less than 1.
    """
    if isinstance(seq, bool) or not isinstance(seq, int):
        raise TypeError("seq must be an exact int")
    if seq < 1:
        raise ValueError("sequence number must be >= 1")
    return ((seq + CHECKPOINT_INTERVAL) // CHECKPOINT_INTERVAL) * CHECKPOINT_INTERVAL - 1


def verify_sequence_gap(headers: Sequence[Union[Dict[str, Any], Any]]) -> bool:
    """Verify that ledger headers have strictly contiguous sequence numbers.

    Args:
        headers: Sequence of ledger header dict-like objects containing 'seq' key.

    Returns:
        True if all sequence numbers increment by exactly 1 without gaps or duplicates;
        False otherwise.
    """
    if len(headers) <= 1:
        return True
    for idx in range(1, len(headers)):
        prev_seq = int(headers[idx - 1].get("seq", 0))
        curr_seq = int(headers[idx].get("seq", 0))
        if curr_seq != prev_seq + 1:
            return False
    return True
