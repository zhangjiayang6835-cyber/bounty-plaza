"""Data structures and enumerations for the OmniBlocks Forever If block subsystem."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class LoopState(str, Enum):
    """Execution state of a loop fiber."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"


class TriggerMode(str, Enum):
    """Trigger mode determining how condition evaluations trigger execution."""

    LEVEL_TRIGGERED = "level_triggered"
    EDGE_TRIGGERED = "edge_triggered"


@dataclass
class BountySettlement:
    """Financial settlement computation based on platform reward policy."""

    reward_usd: float
    platform_coins: float
    contributor_ratio: float
    contributor_coins: float
    redemption_rate_usd: float
    contributor_payout_usd: float
    platform_fee_usd: float
    omb_tokens: float


@dataclass
class FiberStats:
    """Runtime execution metrics for a scheduled loop fiber."""

    fiber_id: str
    state: str
    total_ticks: int
    active_executions: int
    last_condition_result: bool


@dataclass
class BlockNode:
    """Abstract syntax node representing a visual programming block."""

    block_id: str
    block_type: str
    condition_expr: Optional[str] = None
    statements: List[Dict[str, Any]] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
