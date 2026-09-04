import pytest
from scripts.seed_deterministic_verifier_child_bounty_492 import (
    DeterministicVerifierEngine,
    DeterministicTestPayload,
    VerifierHarnessType,
    BountyLifecycle,
)


def test_deterministic_verifier_lifecycle_and_settlement():
    engine = DeterministicVerifierEngine(network="base-mainnet", chain_id=8453)
    creator = "0xCreatorWallet492111111111111111111111111111"
    solver = "0xIndependentSolverWallet492222222222222222"
    parent_id = "0xParentBountyEIP155Round219"
    parent_round = 219

    # 1. Seed child bounty bound to parent
    child = engine.seed_child_bounty(
        creator=creator,
        parent_bounty_id=parent_id,
        parent_round=parent_round,
        work_title="Invariant Replay Harness for Verification Quorum",
        harness_type=VerifierHarnessType.INVARIANT_CHECKER,
        solver_reward=0.90,
        verifier_reward=0.10,
        claim_bond=0.10,
    )
    assert child.status == BountyLifecycle.ACTIVATION_BLOCKED
    assert child.verifier_id == "canonical-child-v1"
    assert child.parent_bounty_id == parent_id
    assert child.parent_round == parent_round

    # 2. Deposit funding
    funding_res = engine.deposit_funding(
        child.child_bounty_id, funder="0xFunderA", amount=1.00, tx_hash="0xTxFunding492"
    )
    assert funding_res["funded"] is True
    assert child.status == BountyLifecycle.CLAIMABLE_LIVE

    # 3. Anti-self-claim protocol enforcement
    with pytest.raises(ValueError, match="Creator cannot self-claim"):
        engine.claim_child_bounty(child.child_bounty_id, solver_wallet=creator, bond_amount=0.10)

    # 4. Independent solver claim
    claim_res = engine.claim_child_bounty(child.child_bounty_id, solver_wallet=solver, bond_amount=0.10)
    assert claim_res["status"] == BountyLifecycle.EXCLUSIVE_CLAIM
    assert child.current_claimant == solver

    # 5. Non-claimant submission rejection
    unauthorized_payload = DeterministicTestPayload(
        suite_name="UnauthSuite",
        harness_type=VerifierHarnessType.INVARIANT_CHECKER,
        assertions=[lambda: True],
        solver_wallet="0xEvilImposter",
        signature="0xSigEvil",
    )
    with pytest.raises(PermissionError, match="Only active claimant"):
        engine.submit_and_execute_verification(child.child_bounty_id, unauthorized_payload)

    # 6. Valid assertion payload and settlement
    valid_payload = DeterministicTestPayload(
        suite_name="InvariantChecks",
        harness_type=VerifierHarnessType.INVARIANT_CHECKER,
        assertions=[
            lambda: 2 + 2 == 4,
            lambda: len("hash") == 4,
            lambda: bool("valid_quorum"),
        ],
        solver_wallet=solver,
        signature="0xSigSolver492",
    )
    settle_res = engine.submit_and_execute_verification(child.child_bounty_id, valid_payload)
    assert settle_res["settled"] is True
    assert settle_res["status"] == BountyLifecycle.SETTLED
    assert settle_res["solver_payout_usdc"] == pytest.approx(1.00)  # 0.90 reward + 0.10 bond return
    assert settle_res["verifier_payout_usdc"] == pytest.approx(0.10)
    assert settle_res["parent_bounty_id"] == parent_id
    assert settle_res["parent_round"] == 219
    assert settle_res["assertions_verified"] == 3
    assert child.settlement_tx_hash.startswith("0x")


def test_failing_assertion_fails_closed():
    engine = DeterministicVerifierEngine()
    child = engine.seed_child_bounty(
        creator="0xCreator492",
        parent_bounty_id="0xParent492",
        parent_round=219,
        work_title="Failing Test Verification",
        harness_type=VerifierHarnessType.FAIL_CLOSED_QUORUM,
    )
    engine.deposit_funding(child.child_bounty_id, "0xFunder", 1.00, "0xTx")
    engine.claim_child_bounty(child.child_bounty_id, "0xSolver492", 0.10)

    failing_payload = DeterministicTestPayload(
        suite_name="FailSuite",
        harness_type=VerifierHarnessType.FAIL_CLOSED_QUORUM,
        assertions=[
            lambda: 10 > 5,
            lambda: 5 == 100,  # Fails
        ],
        solver_wallet="0xSolver492",
        signature="0xSigValid",
    )
    res = engine.submit_and_execute_verification(child.child_bounty_id, failing_payload)
    assert res["settled"] is False
    assert res["status"] == BountyLifecycle.REJECTED
    assert "Assertion index 1 failed" in res["error"]
