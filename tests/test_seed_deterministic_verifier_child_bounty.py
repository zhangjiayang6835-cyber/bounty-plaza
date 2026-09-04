"""Tests for deterministic-verifier child bounty seeding and verification engine.
Validates Issue #502 resolution for NSPG13/agent-bounties#219 / Base Mainnet (EIP-155:8453 autonomous-v1).
"""

import pytest
import sys
from pathlib import Path

# Add bounty-plaza root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.seed_deterministic_verifier_child_bounty import (
    DeterministicVerifierEngine,
    DeterministicTestPayload,
    VerifierTestType,
    BountyLifecycle,
)


def test_seed_and_fund_deterministic_child_bounty():
    engine = DeterministicVerifierEngine()
    bounty = engine.seed_verifier_bounty(
        creator="0xCreatorDeterministic111",
        title="Verify invariant: total supply equals sum of balances",
        test_type=VerifierTestType.CONTRACT_INVARIANT,
        solver_reward=0.90,
        verifier_reward=0.10,
        claim_bond=0.10,
    )

    assert bounty.status == BountyLifecycle.ACTIVATION_BLOCKED
    assert bounty.current_funding_usdc == 0.0

    # Deposit partial funding
    res_partial = engine.deposit_funding(bounty.bounty_id, 0.50, "0xTxPartialFunding")
    assert not res_partial["funded"]
    assert bounty.status == BountyLifecycle.ACTIVATION_BLOCKED

    # Complete required funding (1.00 USDC)
    res_full = engine.deposit_funding(bounty.bounty_id, 0.50, "0xTxFullFunding")
    assert res_full["funded"]
    assert bounty.status == BountyLifecycle.CLAIMABLE_LIVE


def test_claim_bounty_validation():
    engine = DeterministicVerifierEngine()
    bounty = engine.seed_verifier_bounty(
        creator="0xCreatorDeterministic222",
        title="Verify replay gate fixture on transfer race",
        test_type=VerifierTestType.REPLAY_FIXTURE,
        solver_reward=0.90,
        verifier_reward=0.10,
        claim_bond=0.10,
    )
    engine.deposit_funding(bounty.bounty_id, 1.00, "0xDepositTx")

    # Anti-self-claim check
    with pytest.raises(ValueError, match="Creator cannot self-claim"):
        engine.claim_bounty(bounty.bounty_id, "0xCreatorDeterministic222", 0.10)

    # Insufficient bond check
    with pytest.raises(ValueError, match="Bond 0.05 below required 0.1"):
        engine.claim_bounty(bounty.bounty_id, "0xValidSolver333", 0.05)

    # Successful exclusive claim
    claim_res = engine.claim_bounty(bounty.bounty_id, "0xValidSolver333", 0.10)
    assert claim_res["status"] == BountyLifecycle.EXCLUSIVE_CLAIM.value
    assert claim_res["claimant"] == "0xValidSolver333"


def test_successful_deterministic_verification_and_settlement():
    engine = DeterministicVerifierEngine()
    bounty = engine.seed_verifier_bounty(
        creator="0xCreatorDeterministic333",
        title="Verify fail-closed gate auth fixture",
        test_type=VerifierTestType.FAIL_CLOSED_GATE,
        solver_reward=0.90,
        verifier_reward=0.10,
        claim_bond=0.10,
    )
    engine.deposit_funding(bounty.bounty_id, 1.00, "0xDepositFundingTx")
    engine.claim_bounty(bounty.bounty_id, "0xSolverWinner444", 0.10)

    # Define deterministic test execution thunk
    def mock_invariant_suite() -> bool:
        # Invariant checks pass
        state_x = 100
        state_y = 200
        return (state_x + state_y) == 300

    payload = DeterministicTestPayload(
        fixture_id="FIX-GATE-444",
        test_type=VerifierTestType.FAIL_CLOSED_GATE,
        test_code_hash="0xabcd1234ef",
        expected_assertions_count=5,
        test_execution_thunk=mock_invariant_suite,
        solver_signature="0xsig444",
        solver_wallet="0xSolverWinner444",
    )

    settle_res = engine.submit_and_execute_verification(bounty.bounty_id, payload)
    assert settle_res["status"] == BountyLifecycle.SETTLED.value
    assert settle_res["settled"] is True
    assert settle_res["solver_payout_usdc"] == 1.00  # 0.90 reward + 0.10 bond returned
    assert settle_res["verifier_payout_usdc"] == 0.10
    assert settle_res["assertions_verified"] == 5
    assert bounty.settlement_tx_hash is not None


def test_failed_deterministic_verification_rejection():
    engine = DeterministicVerifierEngine()
    bounty = engine.seed_verifier_bounty(
        creator="0xCreatorDeterministic555",
        title="Verify state machine transition replay",
        test_type=VerifierTestType.STATE_MACHINE_TRANSITION,
    )
    engine.deposit_funding(bounty.bounty_id, 1.00, "0xDepositFundingTx")
    engine.claim_bounty(bounty.bounty_id, "0xSolverFailing555", 0.10)

    def failing_test_suite() -> bool:
        return False

    payload = DeterministicTestPayload(
        fixture_id="FIX-FAIL-555",
        test_type=VerifierTestType.STATE_MACHINE_TRANSITION,
        test_code_hash="0xbadhash",
        expected_assertions_count=3,
        test_execution_thunk=failing_test_suite,
        solver_signature="0xbad",
        solver_wallet="0xSolverFailing555",
    )

    res = engine.submit_and_execute_verification(bounty.bounty_id, payload)
    assert res["status"] == BountyLifecycle.REJECTED.value
    assert res["settled"] is False
    assert "assertions failed" in res["error"]
