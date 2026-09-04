"""Lifecycle-Aware Activation Reconciliation Engine & Behavioral State Machine.
Resolves Issue #735: [Bounty] [DIRECT] Make activation reconciliation lifecycle-aware.

Live Payment Evidence:
- Contract: 0x2afb91d160200fac4b91e6134b2cc9d9bff86f42
- Network: Base mainnet (EIP-155:8453)
- Payout: 1.99 USDC, Bond: 0.01 USDC, Funding: 2.00 / 2.00 USDC

Acceptance Criteria:
- Models canonical factory and hosted feed state across all four active statuses:
  claimable, claimed, submitted, and verifying.
- Enforces that no planner or send transaction path runs for an already-canonical contract.
- Invalid terms, unavailable verification, terminal failure, and ambiguity fail closed.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class LifecycleStatus(str, Enum):
    CLAIMABLE = "claimable"
    CLAIMED = "claimed"
    SUBMITTED = "submitted"
    VERIFYING = "verifying"
    SETTLED = "settled"
    FAILED = "failed"


ACTIVE_LIFECYCLE_STATUSES: Set[LifecycleStatus] = {
    LifecycleStatus.CLAIMABLE,
    LifecycleStatus.CLAIMED,
    LifecycleStatus.SUBMITTED,
    LifecycleStatus.VERIFYING,
}


@dataclass
class OnChainBountyContract:
    contract_address: str
    discovery_id: str
    network: str
    status: LifecycleStatus
    confirmed_funding_usdc: float
    required_funding_usdc: float
    terms_valid: bool
    verifier_available: bool
    terminal_failure: bool = False
    is_ambiguous: bool = False


@dataclass
class ReconciliationDecision:
    action: str
    status: str
    planner_triggered: bool
    send_path_executed: bool
    reason: str
    contract_address: Optional[str] = None
    fail_closed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "status": self.status,
            "planner_triggered": self.planner_triggered,
            "send_path_executed": self.send_path_executed,
            "reason": self.reason,
            "contract_address": self.contract_address,
            "fail_closed": self.fail_closed,
        }


class ActivationReconciliationEngine:
    """Reconciles canonical factory and hosted feeds with on-chain states."""

    def __init__(self):
        # Maps discovery_id -> OnChainBountyContract
        self.canonical_registry: Dict[str, OnChainBountyContract] = {}
        # Track deploy planner and send executions
        self.planner_runs: int = 0
        self.send_tx_count: int = 0

    def register_canonical_contract(self, contract: OnChainBountyContract):
        self.canonical_registry[contract.discovery_id] = contract

    def reconcile_activation(self, discovery_id: str, candidate_contract: Optional[OnChainBountyContract] = None) -> ReconciliationDecision:
        """Evaluates activation candidate against canonical state and enforces lifecycle rules."""
        active_contract = self.canonical_registry.get(discovery_id, candidate_contract)

        if active_contract is None:
            # New un-instantiated bounty: safe to plan deployment
            self.planner_runs += 1
            self.send_tx_count += 1
            return ReconciliationDecision(
                action="DEPLOY_NEW_CONTRACT",
                status="PLANNED",
                planner_triggered=True,
                send_path_executed=True,
                reason="No canonical contract registered; initiating clean deployment.",
            )

        # 1. Fail Closed Check: Invalid Terms
        if not active_contract.terms_valid:
            return ReconciliationDecision(
                action="REJECT_ACTIVATION",
                status="FAIL_CLOSED",
                planner_triggered=False,
                send_path_executed=False,
                reason="Invalid terms detected; activation rejected fail-closed.",
                contract_address=active_contract.contract_address,
                fail_closed=True,
            )

        # 2. Fail Closed Check: Unavailable Verification
        if not active_contract.verifier_available:
            return ReconciliationDecision(
                action="REJECT_ACTIVATION",
                status="FAIL_CLOSED",
                planner_triggered=False,
                send_path_executed=False,
                reason="Verifier suite unavailable or quorum offline; activation rejected fail-closed.",
                contract_address=active_contract.contract_address,
                fail_closed=True,
            )

        # 3. Fail Closed Check: Terminal Failure
        if active_contract.terminal_failure or active_contract.status == LifecycleStatus.FAILED:
            return ReconciliationDecision(
                action="REJECT_ACTIVATION",
                status="FAIL_CLOSED",
                planner_triggered=False,
                send_path_executed=False,
                reason="Terminal contract failure recorded; activation rejected fail-closed.",
                contract_address=active_contract.contract_address,
                fail_closed=True,
            )

        # 4. Fail Closed Check: Ambiguity or State Collision
        if active_contract.is_ambiguous:
            return ReconciliationDecision(
                action="REJECT_ACTIVATION",
                status="FAIL_CLOSED",
                planner_triggered=False,
                send_path_executed=False,
                reason="Ambiguous state or multiple conflicting instances detected; activation rejected fail-closed.",
                contract_address=active_contract.contract_address,
                fail_closed=True,
            )

        # 5. Already-Canonical Lifecycle Protection:
        # If contract is already canonical across ANY of the 4 active statuses:
        # (claimable, claimed, submitted, verifying)
        # NEVER run the planner or send path! Resume the existing lifecycle cleanly.
        if active_contract.status in ACTIVE_LIFECYCLE_STATUSES:
            return ReconciliationDecision(
                action=f"RESUME_{active_contract.status.name}_LIFECYCLE",
                status=active_contract.status.value,
                planner_triggered=False,
                send_path_executed=False,
                reason=(
                    f"Contract {active_contract.contract_address} is already canonical in "
                    f"status '{active_contract.status.value}'. Deployment planner and send path suppressed."
                ),
                contract_address=active_contract.contract_address,
                fail_closed=False,
            )

        # Settled state
        if active_contract.status == LifecycleStatus.SETTLED:
            return ReconciliationDecision(
                action="ARCHIVE_SETTLED_CONTRACT",
                status="settled",
                planner_triggered=False,
                send_path_executed=False,
                reason=f"Contract {active_contract.contract_address} is fully settled on-chain.",
                contract_address=active_contract.contract_address,
                fail_closed=False,
            )

        # Catch-all safety: fail-closed on unknown status
        return ReconciliationDecision(
            action="REJECT_UNKNOWN_STATE",
            status="FAIL_CLOSED",
            planner_triggered=False,
            send_path_executed=False,
            reason="Unrecognized lifecycle state encountered; failing closed.",
            contract_address=active_contract.contract_address,
            fail_closed=True,
        )
