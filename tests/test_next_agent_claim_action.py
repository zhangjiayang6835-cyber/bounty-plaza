"""Unit test suite and benchmark verification for Next Agent Claim Action Mapper.
Tests Issue #951 requirements:
- Canonical Base Mainnet discovery benchmark state mappings
- Verification pending -> INSPECT_VERIFICATION_WORK
- Unclaimed + escrowed -> POST_CLAIM_BOND
- Active claim by solver -> SUBMIT_SOLUTION_PAYLOAD
- Dispute handling on verification failure
- Settlement receipt confirmation
- Unfunded escrow rejection
"""

import pytest
from scripts.next_agent_claim_action import (
    BountyContext,
    ClaimAction,
    ClaimNextActionMapper,
    CompetitionState,
    PaymentState,
    WorkState,
)


def test_benchmark_canonical_issue_951_verification_pending():
    """Validates the exact canonical benchmark case specified in Issue #951:

    work_state: verification_pending
    payment_state: escrowed
    competition_state: exclusive_claim
    solver_reward: 0.99 USDC
    entry_bond: 0.01 USDC
    verifier: signed_quorum (ready: True)
    """
    ctx = BountyContext(
        discovery_id="eip155:8453:agent-bounties/autonomous-v1:0xa067be3a248beb204213222cab2b1c3a2b8746fe",
        work_state=WorkState.VERIFICATION_PENDING,
        payment_state=PaymentState.ESCROWED,
        competition_state=CompetitionState.EXCLUSIVE_CLAIM,
        solver_reward_usdc=0.99,
        entry_bond_usdc=0.01,
        verifier_ready=True,
    )

    action_res = ClaimNextActionMapper.map_next_action(ctx)
    assert action_res["action"] == ClaimAction.INSPECT_VERIFICATION_WORK.value
    assert action_res["urgency"] == "HIGH"
    assert action_res["can_execute"] is True
    assert "inspection_url" in action_res
    assert "0xa067be3a248beb204213222cab2b1c3a2b8746fe" in action_res["inspection_url"]


def test_unclaimed_escrowed_post_bond():
    ctx = BountyContext(
        discovery_id="eip155:8453:agent-bounties/autonomous-v1:0x123",
        work_state=WorkState.UNCLAIMED,
        payment_state=PaymentState.ESCROWED,
        competition_state=CompetitionState.OPEN_RACE,
        solver_reward_usdc=50.0,
        entry_bond_usdc=2.5,
        verifier_ready=True,
    )
    res = ClaimNextActionMapper.map_next_action(ctx)
    assert res["action"] == ClaimAction.POST_CLAIM_BOND.value
    assert res["required_bond"] == 2.5
    assert res["can_execute"] is True


def test_active_claim_solver_solution_submission():
    ctx = BountyContext(
        discovery_id="eip155:8453:agent-bounties/autonomous-v1:0x456",
        work_state=WorkState.CLAIMED,
        payment_state=PaymentState.ESCROWED,
        competition_state=CompetitionState.EXCLUSIVE_CLAIM,
        solver_reward_usdc=100.0,
        entry_bond_usdc=5.0,
        verifier_ready=True,
        is_current_solver=True,
    )
    res = ClaimNextActionMapper.map_next_action(ctx)
    assert res["action"] == ClaimAction.SUBMIT_SOLUTION_PAYLOAD.value
    assert res["can_execute"] is True


def test_dispute_on_verification_failure():
    ctx = BountyContext(
        discovery_id="eip155:8453:agent-bounties/autonomous-v1:0x789",
        work_state=WorkState.VERIFICATION_FAILED,
        payment_state=PaymentState.ESCROWED,
        competition_state=CompetitionState.EXCLUSIVE_CLAIM,
        solver_reward_usdc=75.0,
        entry_bond_usdc=3.0,
        verifier_ready=True,
    )
    res = ClaimNextActionMapper.map_next_action(ctx)
    assert res["action"] == ClaimAction.DISPUTE_VERIFIER_QUORUM.value
    assert res["urgency"] == "CRITICAL"


def test_settled_receipt_confirmation():
    ctx = BountyContext(
        discovery_id="eip155:8453:agent-bounties/autonomous-v1:0xabc",
        work_state=WorkState.SETTLED,
        payment_state=PaymentState.SETTLED,
        competition_state=CompetitionState.CLOSED,
        solver_reward_usdc=250.0,
        entry_bond_usdc=10.0,
        verifier_ready=True,
    )
    res = ClaimNextActionMapper.map_next_action(ctx)
    assert res["action"] == ClaimAction.CONFIRM_SETTLEMENT_RECEIPT.value
    assert res["urgency"] == "COMPLETED"


def test_unfunded_bounty_awaits_escrow():
    ctx = BountyContext(
        discovery_id="eip155:8453:agent-bounties/autonomous-v1:0xdef",
        work_state=WorkState.UNCLAIMED,
        payment_state=PaymentState.UNFUNDED,
        competition_state=CompetitionState.OPEN_RACE,
        solver_reward_usdc=500.0,
        entry_bond_usdc=25.0,
        verifier_ready=False,
    )
    res = ClaimNextActionMapper.map_next_action(ctx)
    assert res["action"] == ClaimAction.AWAIT_ESCROW_FUNDING.value
    assert res["can_execute"] is False
