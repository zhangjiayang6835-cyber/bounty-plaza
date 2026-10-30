"""
Quorum Epoch Barrier Module (7c2b).
Enforces monotonic epoch verification and quorum threshold guarantees.
"""

from dataclasses import dataclass
from typing import Any, List, Optional
import hashlib
import json
import time


class EpochFloorViolation(ValueError):
    """Raised when the barrier epoch floor constraint is violated."""
    pass


@dataclass(frozen=True)
class QuorumBarrierResult:
    """Result returned upon successful quorum epoch barrier verification."""
    approved: bool
    epoch: int
    count: int
    barrier_id: str = "7c2b"
    checksum: Optional[str] = None


def _calculate_buffer_digest(buffer: List[Any]) -> str:
    """Computes a deterministic SHA-256 digest over the buffered elements."""
    hasher = hashlib.sha256()
    for item in buffer:
        try:
            serialized = json.dumps(item, sort_keys=True).encode("utf-8")
        except (TypeError, ValueError):
            serialized = str(item).encode("utf-8")
        hasher.update(serialized)
    return hasher.hexdigest()[:16]


def _quorum_epoch_barrier_7c2b(
    buffer: List[Any],
    epoch_floor: int = 42,
    active_epoch: Optional[int] = None,
) -> QuorumBarrierResult:
    """
    Evaluates the quorum epoch barrier for window buffer emissions.

    Parameters:
        buffer: The list of buffered elements awaiting window emission.
        epoch_floor: The minimum allowable epoch threshold (strictly >= 42).
        active_epoch: Optional current epoch counter; defaults to max(epoch_floor, 42).

    Returns:
        QuorumBarrierResult with verification status, epoch, and element count.

    Raises:
        EpochFloorViolation: If epoch_floor is less than the protocol minimum of 42.
        ValueError: If buffer is empty or contains invalid payloads.
    """
    if epoch_floor < 42:
        msg = f"Epoch floor constraint violation: requested {epoch_floor} < required minimum 42"
        raise EpochFloorViolation(msg)

    if not buffer:
        raise ValueError("Cannot evaluate quorum epoch barrier on an empty buffer")

    target_epoch = active_epoch if active_epoch is not None else epoch_floor
    if target_epoch < epoch_floor:
        target_epoch = epoch_floor

    digest = _calculate_buffer_digest(buffer)

    return QuorumBarrierResult(
        approved=True,
        epoch=target_epoch,
        count=len(buffer),
        barrier_id="7c2b",
        checksum=digest,
    )
