"""Ledger sequence validator module (#4256).

Provides sequence gap verification for ledger headers ensuring contiguous sequence numbers
and mandatory sequence key validation.
"""

from __future__ import annotations


def verify_sequence_gap(headers: list[dict[str, int]]) -> bool:
    """Verify that ledger headers have strictly contiguous sequence numbers.

    Args:
        headers: List of ledger header dictionaries containing sequence identifiers.

    Returns:
        True if ledger headers form a strictly contiguous sequence (+1 per entry);
        False if there is a gap or out-of-order sequence.

    Raises:
        KeyError: If any header dictionary in the list does not contain the 'seq' key.
    """
    for header in headers:
        if "seq" not in header:
            raise KeyError("missing seq key in header")

    if len(headers) <= 1:
        return True

    for idx in range(1, len(headers)):
        prev_seq = int(headers[idx - 1]["seq"])
        curr_seq = int(headers[idx]["seq"])
        if curr_seq != prev_seq + 1:
            return False

    return True
