"""Next Agent Claim Action Mapper and Benchmark State Machine.
Resolves Issue #951: [Bounty] Repair claim next-action mapper.

Canonical Protocol Spec (Base Mainnet EIP-155:8453 autonomous-v1):
- Maps combinations of (work_state, payment_state, competition_state, verifier_status)
  to deterministically prioritized solver next-actions.
- Resolves benchmark cases:
  1. verification_pending + escrowed + exclusive_claim -> INSPECT_VERIFICATION_WORK
  2. unclaimed + escrowed + open_race -> POST_CLAIM_BOND
  3. claimed + escrowed + exclusive_claim (current solver) -> SUBMIT_SOLUTION_PAYLOAD
  4. verification_failed + escrowed -> DISPUTE_VERIFIER_QUORUM
  5. settled + settled -> CONFIRM_SETTLEMENT_RECEIPT
  6. unfunded -> AWAIT_ESCROW_FUNDING
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class WorkState(str, Enum):
    UNCLAIMED = "unclaimed"
    CLAIMED = "claimed"
    VERIFICATION_PENDING = "verification_pending"
    VERIFICATION_FAILED = "verification_failed"
    SETTLED = "settled"
    ABANDONED = "abandoned"


class PaymentState(str, Enum):
    UNFUNDED = "unfunded"
    ESCROWED = "escrowed"
    SETTLED = "settled"
    REFUNDED = "refunded"


class CompetitionState(str, Enum):
    OPEN_RACE = "open_race"
    EXCLUSIVE_CLAIM = "exclusive_claim"
    CLOSED = "closed"


class ClaimAction(str, Enum):
    AWAIT_ESCROW_FUNDING = "AWAIT_ESCROW_FUNDING"
    POST_CLAIM_BOND = "POST_CLAIM_BOND"
    SUBMIT_SOLUTION_PAYLOAD = "SUBMIT_SOLUTION_PAYLOAD"
    INSPECT_VERIFICATION_WORK = "INSPECT_VERIFICATION_WORK"
    WAIT_FOR_VERIFIER_QUORUM = "WAIT_FOR_VERIFIER_QUORUM"
    DISPUTE_VERIFIER_QUORUM = "DISPUTE_VERIFIER_QUORUM"
    CONFIRM_SETTLEMENT_RECEIPT = "CONFIRM_SETTLEMENT_RECEIPT"
    NO_ACTION_REQUIRED = "NO_ACTION_REQUIRED"


@dataclass
class BountyContext:
    discovery_id: str
    work_state: WorkState
    payment_state: PaymentState
    competition_state: CompetitionState
    solver_reward_usdc: float
    entry_bond_usdc: float
    verifier_ready: bool
    is_current_solver: bool = False
    contract_address: Optional[str] = None


class ClaimNextActionMapper:
    """Evaluates canonical bounty discovery state and outputs the next deterministic action."""

    @classmethod
    def map_next_action(cls, ctx: BountyContext) -> Dict[str, Any]:
        # 1. Unfunded state takes precedence — no work can be secured without escrow
        if ctx.payment_state == PaymentState.UNFUNDED:
            return {
                "action": ClaimAction.AWAIT_ESCROW_FUNDING.value,
                "urgency": "LOW",
                "reason": "Escrow balance is 0; awaiting creator deposit.",
                "can_execute": False,
                "required_bond": 0.0,
            }

        # 2. Settled state
        if ctx.work_state == WorkState.SETTLED or ctx.payment_state == PaymentState.SETTLED:
            return {
                "action": ClaimAction.CONFIRM_SETTLEMENT_RECEIPT.value,
                "urgency": "COMPLETED",
                "reason": "Bounty has been verified and settled on-chain.",
                "can_execute": True,
                "required_bond": 0.0,
            }

        # 3. Verification Pending — inspect verification work or wait for quorum
        if ctx.work_state == WorkState.VERIFICATION_PENDING:
            action = ClaimAction.INSPECT_VERIFICATION_WORK.value if ctx.verifier_ready else ClaimAction.WAIT_FOR_VERIFIER_QUORUM.value
            return {
                "action": action,
                "urgency": "HIGH",
                "reason": "Solution is committed and awaiting signed quorum verification.",
                "can_execute": ctx.verifier_ready,
                "required_bond": 0.0,
                "inspection_url": f"https://api.agentbounties.app/v1/base/autonomous-bounties/verification-jobs?discovery_id={ctx.discovery_id}",
            }

        # 4. Verification Failed — dispute or retry
        if ctx.work_state == WorkState.VERIFICATION_FAILED:
            return {
                "action": ClaimAction.DISPUTE_VERIFIER_QUORUM.value,
                "urgency": "CRITICAL",
                "reason": "Verifier quorum rejected initial submission; inspection or dispute required.",
                "can_execute": True,
                "required_bond": 0.0,
            }

        # 5. Active Claimed State
        if ctx.work_state == WorkState.CLAIMED:
            if ctx.is_current_solver:
                return {
                    "action": ClaimAction.SUBMIT_SOLUTION_PAYLOAD.value,
                    "urgency": "HIGH",
                    "reason": "Exclusive claim active. Solver must submit solution payload before expiry.",
                    "can_execute": True,
                    "required_bond": 0.0,
                }
            return {
                "action": ClaimAction.NO_ACTION_REQUIRED.value,
                "urgency": "BLOCKED",
                "reason": "Another solver holds exclusive claim on this bounty.",
                "can_execute": False,
                "required_bond": 0.0,
            }

        # 6. Unclaimed & Escrowed -> Ready to claim
        if ctx.work_state == WorkState.UNCLAIMED and ctx.payment_state == PaymentState.ESCROWED:
            return {
                "action": ClaimAction.POST_CLAIM_BOND.value,
                "urgency": "IMMEDIATE",
                "reason": f"Bounty is open for claim. Requires {ctx.entry_bond_usdc:.2f} USDC entry bond.",
                "can_execute": True,
                "required_bond": ctx.entry_bond_usdc,
            }

        return {
            "action": ClaimAction.NO_ACTION_REQUIRED.value,
            "urgency": "NONE",
            "reason": "No pending transitions.",
            "can_execute": False,
            "required_bond": 0.0,
        }
