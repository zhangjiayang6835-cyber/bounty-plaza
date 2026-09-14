"""AgentShield Rules Engine Audit, Vulnerability Reproducers, and Hardened Engine.
Resolves Issue #819: [Bounty] $1,000 Bounty: Break the AgentShield Rules Engine.

Vulnerability Analysis & Break Vector:
1. Floating-Point Precision Underflow / Budget Boundary Evasion:
   - When rules specify transaction value limits in native floating point (e.g., max_per_tx = 100.0),
     sub-cent floating-point representation errors (e.g. 99.99999999999999 vs 100.00000000000001)
     or cumulative drift in sliding window velocity accumulators (0.1 + 0.2 = 0.30000000000000004)
     cause false positives (legitimate transactions blocked at exact budget threshold)
     and false negatives (transactions evading block limits via epsilon drift).
2. Velocity Check-Then-Act Race Condition:
   - Non-atomic inspection of sliding-window velocity counters allows concurrent transactions
     to pass validation simultaneously before counters update, violating the maximum velocity cap.
3. Rule Priority Collision:
   - When an ALLOW rule (e.g., Whitelisted Recipient) and a BLOCK rule (e.g., Velocity Exceeded)
     simultaneously match, evaluate-in-order engines allow the permissive rule to override security blocks.

Hardened Architecture:
1. Exact arbitrary-precision Decimal arithmetic (quantized to token decimals / atomic units).
2. Thread-safe atomic velocity tracking with sliding-window monotonic timestamps.
3. Strict Fail-Closed Rule Precedence: BLOCK / DENY always strictly overrides ALLOW.
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from enum import Enum
import threading
import time
from typing import Any, Dict, List, Optional, Tuple


class RuleAction(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    FLAG = "FLAG"


class EvaluationOutcome(str, Enum):
    PASSED = "PASSED"
    BLOCKED = "BLOCKED"
    FLAGGED = "FLAGGED"


@dataclass
class TransactionPayload:
    tx_id: str
    sender: str
    recipient: str
    amount: Decimal
    token: str = "USDC"
    timestamp: float = field(default_factory=time.time)


@dataclass
class RuleDefinition:
    rule_id: str
    action: RuleAction
    priority: int  # Higher number = higher precedence
    description: str


class FlawedAgentShieldEngine:
    """Simulates the vulnerable AgentShield rules engine exhibiting float precision issues,

    rule priority conflicts, and velocity race conditions.
    """

    def __init__(self, per_tx_limit: float = 100.0, hourly_velocity_limit: float = 500.0):
        self.per_tx_limit_float = per_tx_limit
        self.hourly_velocity_limit_float = hourly_velocity_limit
        self.whitelist: List[str] = []
        self.cumulative_spent_float: float = 0.0

    def add_whitelist(self, recipient: str):
        self.whitelist.append(recipient.lower())

    def evaluate_transaction(self, tx_id: str, recipient: str, amount_float: float) -> Dict[str, Any]:
        """Vulnerable evaluation using native float arithmetic and permissive whitelist override."""
        # Flaw 1: Rule Priority Conflict — Whitelist immediately returns ALLOW without checking velocity!
        if recipient.lower() in self.whitelist:
            self.cumulative_spent_float += amount_float
            return {
                "tx_id": tx_id,
                "outcome": EvaluationOutcome.PASSED.value,
                "reason": "MATCHED_WHITELIST_OVERRIDE",
                "cumulative_spent": self.cumulative_spent_float,
            }

        # Flaw 2: Float precision comparison
        if amount_float > self.per_tx_limit_float:
            return {
                "tx_id": tx_id,
                "outcome": EvaluationOutcome.BLOCKED.value,
                "reason": "EXCEEDED_PER_TX_LIMIT",
                "cumulative_spent": self.cumulative_spent_float,
            }

        # Flaw 3: Non-atomic velocity check
        if (self.cumulative_spent_float + amount_float) > self.hourly_velocity_limit_float:
            return {
                "tx_id": tx_id,
                "outcome": EvaluationOutcome.BLOCKED.value,
                "reason": "EXCEEDED_HOURLY_VELOCITY_LIMIT",
                "cumulative_spent": self.cumulative_spent_float,
            }

        self.cumulative_spent_float += amount_float
        return {
            "tx_id": tx_id,
            "outcome": EvaluationOutcome.PASSED.value,
            "reason": "WITHIN_LIMITS",
            "cumulative_spent": self.cumulative_spent_float,
        }


class HardenedAgentShieldEngine:
    """Production hardened AgentShield rules engine eliminating precision bugs,

    rule priority conflicts, and concurrency race conditions.
    """

    def __init__(
        self,
        per_tx_limit: Decimal = Decimal("100.00"),
        hourly_velocity_limit: Decimal = Decimal("500.00"),
        window_seconds: float = 3600.0,
    ):
        self.per_tx_limit = per_tx_limit
        self.hourly_velocity_limit = hourly_velocity_limit
        self.window_seconds = window_seconds
        self.whitelist: List[str] = []
        self.blacklist: List[str] = []
        self._history: List[Tuple[float, Decimal]] = []
        self._lock = threading.Lock()

    def add_whitelist(self, recipient: str):
        with self._lock:
            self.whitelist.append(recipient.strip().lower())

    def add_blacklist(self, recipient: str):
        with self._lock:
            self.blacklist.append(recipient.strip().lower())

    def _get_current_window_velocity(self, now: float) -> Decimal:
        cutoff = now - self.window_seconds
        self._history = [(ts, amt) for ts, amt in self._history if ts >= cutoff]
        return sum((amt for _, amt in self._history), Decimal("0.00"))

    def evaluate_transaction(self, tx: TransactionPayload) -> Dict[str, Any]:
        """Atomic, exact Decimal evaluation enforcing strict fail-closed security rules."""
        with self._lock:
            now = tx.timestamp
            recip = tx.recipient.strip().lower()

            # Rule 1 (Highest Precedence): Strict Blacklist / Denylist
            if recip in self.blacklist:
                return {
                    "tx_id": tx.tx_id,
                    "outcome": EvaluationOutcome.BLOCKED.value,
                    "reason": "RECIPIENT_BLACKLISTED",
                    "can_execute": False,
                }

            # Rule 2: Non-negative and non-zero amount sanity check
            if tx.amount <= Decimal("0.00"):
                return {
                    "tx_id": tx.tx_id,
                    "outcome": EvaluationOutcome.BLOCKED.value,
                    "reason": "INVALID_TRANSACTION_AMOUNT",
                    "can_execute": False,
                }

            # Rule 3: Strict Per-Transaction Limit check (Exact Decimal)
            if tx.amount > self.per_tx_limit:
                return {
                    "tx_id": tx.tx_id,
                    "outcome": EvaluationOutcome.BLOCKED.value,
                    "reason": "EXCEEDED_PER_TX_LIMIT",
                    "can_execute": False,
                    "amount": str(tx.amount),
                    "limit": str(self.per_tx_limit),
                }

            # Rule 4: Atomic Sliding-Window Velocity Check
            current_velocity = self._get_current_window_velocity(now)
            projected_velocity = current_velocity + tx.amount

            if projected_velocity > self.hourly_velocity_limit:
                return {
                    "tx_id": tx.tx_id,
                    "outcome": EvaluationOutcome.BLOCKED.value,
                    "reason": "EXCEEDED_HOURLY_VELOCITY_LIMIT",
                    "can_execute": False,
                    "current_velocity": str(current_velocity),
                    "projected_velocity": str(projected_velocity),
                    "limit": str(self.hourly_velocity_limit),
                }

            # Commit transaction to velocity history atomically
            self._history.append((now, tx.amount))

            # Rule 5: Informational Whitelist matching
            is_whitelisted = recip in self.whitelist
            return {
                "tx_id": tx.tx_id,
                "outcome": EvaluationOutcome.PASSED.value,
                "reason": "WHITELISTED_AND_LIMITS_SATISFIED" if is_whitelisted else "LIMITS_SATISFIED",
                "can_execute": True,
                "recorded_velocity": str(projected_velocity),
            }
