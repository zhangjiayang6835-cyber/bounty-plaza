"""Unit tests for Autonomous Distribution Child Bounty Seeding Subsystem.
Resolves Issue #503: [Bounty] [NSPG13/agent-bounties] [1 USDC autonomous bounty] Seed a distribution child bounty.
Validates:
- Complete lifecycle: SEED -> FUND -> CLAIM -> SUBMIT -> SETTLE
- Enforces root funding threshold (1.00 USDC = 0.90 solver + 0.10 verifier)
- Prevents self-claims by bounty creator
- Enforces 0.10 USDC entry claim bond
- Validates cryptographic proof payload integrity
- Confirms BountySettled event and solver reward + bond release
"""

import pytest
from scripts.seed_distribution_child_bounty import (
    AutonomousDistributionEngine,
    BountyLifecycle,
    DistributionLane,
    DistributionProofPayload,
)


def test_full_bounty_lifecycle_seed_to_settlement():
    engine = AutonomousDistributionEngine()
    creator = "0x1111111111111111111111111111111111111111"
    solver = "0x2222222222222222222222222222222222222222"
    verifier = "0x3333333333333333333333333333333333333333"

    # 1. Seed child bounty
    bounty = engine.seed_child_bounty(
        creator=creator,
        title="Distribute Agent Bounties on HuggingFace Hub and Reddit",
        lane=DistributionLane.SOCIAL_SHARE,
        solver_reward=0.90,
        verifier_reward=0.10,
        claim_bond=0.10,
    )
    assert bounty.status == BountyLifecycle.ACTIVATION_BLOCKED
    assert bounty.current_funding_usdc == 0.0

    # 2. Deposit root funding (1.00 USDC)
    fund_res = engine.deposit_root_funding(
        bounty_id=bounty.bounty_id,
        amount_usdc=1.00,
        tx_hash="0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
    )
    assert fund_res["status"] == BountyLifecycle.CLAIMABLE_LIVE.value
    assert fund_res["funded"] is True

    # 3. Solver claims with 0.10 USDC bond
    claim_res = engine.claim_bounty(
        bounty_id=bounty.bounty_id,
        solver_address=solver,
        bond_amount=0.10,
    )
    assert claim_res["status"] == BountyLifecycle.EXCLUSIVE_CLAIM.value
    assert claim_res["claimant"] == solver

    # 4. Submit distribution solution payload
    proof = DistributionProofPayload(
        solver_address=solver,
        target_bounty_id=bounty.bounty_id,
        action_lane=DistributionLane.SOCIAL_SHARE,
        proof_url="https://huggingface.co/posts/agent-bounties-distribution-demo",
        engagement_metrics={"views": 1500, "upvotes": 42},
        cryptographic_signature="0x" + "a" * 130,
    )
    assert proof.verify_integrity() is True

    sub_res = engine.submit_distribution_solution(proof)
    assert sub_res["status"] == BountyLifecycle.VERIFICATION_PENDING.value

    # 5. Verifier approves and settles
    settle_res = engine.settle_bounty(
        bounty_id=bounty.bounty_id,
        verifier_address=verifier,
        approved=True,
    )
    assert settle_res["status"] == BountyLifecycle.SETTLED.value
    assert settle_res["settled"] is True
    assert settle_res["solver_payout_usdc"] == 1.00  # 0.90 reward + 0.10 returned bond
    assert settle_res["verifier_payout_usdc"] == 0.10
    assert settle_res["settlement_tx_hash"].startswith("0x")


def test_creator_cannot_claim_own_bounty():
    engine = AutonomousDistributionEngine()
    creator = "0x4444444444444444444444444444444444444444"

    bounty = engine.seed_child_bounty(
        creator=creator,
        title="Index canonical bounties in search aggregators",
        lane=DistributionLane.DISCOVERY_INDEXING,
    )
    engine.deposit_root_funding(bounty.bounty_id, 1.00, "0x999")

    with pytest.raises(ValueError, match="Creator cannot claim their own"):
        engine.claim_bounty(bounty.bounty_id, solver_address=creator, bond_amount=0.10)


def test_insufficient_claim_bond_rejected():
    engine = AutonomousDistributionEngine()
    creator = "0x5555555555555555555555555555555555555555"
    solver = "0x6666666666666666666666666666666666666666"

    bounty = engine.seed_child_bounty(
        creator=creator,
        title="Star and upvote demonstration pipeline",
        lane=DistributionLane.STAR_UPVOTE_PROOF,
        claim_bond=0.10,
    )
    engine.deposit_root_funding(bounty.bounty_id, 1.00, "0x888")

    with pytest.raises(ValueError, match="Bond 0.05 USDC insufficient"):
        engine.claim_bounty(bounty.bounty_id, solver_address=solver, bond_amount=0.05)


def test_proof_integrity_validation():
    # Valid
    p_valid = DistributionProofPayload(
        solver_address="0x" + "1" * 40,
        target_bounty_id="0xabc",
        action_lane=DistributionLane.REFERRAL_ONBOARDING,
        proof_url="https://github.com/agent-bounties/activity/1",
        engagement_metrics={"referrals": 5},
        cryptographic_signature="0x" + "f" * 130,
    )
    assert p_valid.verify_integrity() is True

    # Invalid URL
    p_bad_url = DistributionProofPayload(
        solver_address="0x" + "1" * 40,
        target_bounty_id="0xabc",
        action_lane=DistributionLane.REFERRAL_ONBOARDING,
        proof_url="not_a_valid_url",
        engagement_metrics={},
        cryptographic_signature="0x" + "f" * 130,
    )
    assert p_bad_url.verify_integrity() is False
