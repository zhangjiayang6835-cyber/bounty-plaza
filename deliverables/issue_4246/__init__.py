"""Deliverables package for Issue #4246."""

from .ledger_validator import (
    CANONICAL_GAP_CONTRACT,
    CHECKPOINT_INTERVAL,
    compute_checkpoint_boundary,
    verify_sequence_gap,
)

__all__ = [
    "CANONICAL_GAP_CONTRACT",
    "CHECKPOINT_INTERVAL",
    "compute_checkpoint_boundary",
    "verify_sequence_gap",
]
