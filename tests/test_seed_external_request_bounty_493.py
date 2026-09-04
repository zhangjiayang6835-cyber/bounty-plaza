import pytest
from scripts.seed_external_request_bounty_493 import (
    CanonicalChildBountyEngine,
    ChildBenchmarkProof,
    ExternalWorkCategory,
    BountyLifecycle,
)


def test_pii_redaction_sanitization():
    raw_desc = (
        "Task: extract table from invoice. Contact me at client_99@partner.org or call +1 415-555-0199. "
        "Use api_key='mock_custom_key_9876543210abcdef0123456789' to pull files."
    )
    sanitized = CanonicalChildBountyEngine.redact_pii(raw_desc)
    assert "client_99@partner.org" not in sanitized
    assert "[REDACTED_EMAIL]" in sanitized
    assert "+1 415-555-0199" not in sanitized
    assert "[REDACTED_PHONE]" in sanitized
    assert "mock_custom_key_9876543210abcdef0123456789" not in sanitized
    assert "[REDACTED_SECRET]" in sanitized


def test_canonical_child_bounty_full_lifecycle():
    engine = CanonicalChildBountyEngine(network="base-mainnet", chain_id=8453)
    creator = "0xCreatorWallet11111111111111111111111111111111"
    external_requester = "0xRequesterWallet2222222222222222222222222222"
    independent_solver = "0xSolverWallet333333333333333333333333333333"

    parent_id = "0xParentBountyEIP155Round493"
    parent_round = 493

    # 1. Seed canonical child bounty
    child = engine.seed_canonical_child_bounty(
        creator=creator,
        parent_bounty_id=parent_id,
        parent_round=parent_round,
        external_requester=external_requester,
        work_title="Normalize Multimodal Telemetry",
        raw_description="Normalize logs for user contact@example.com with api_key=abcdef0123456789a1b2c3d4",
        category=ExternalWorkCategory.DATA_NORMALIZATION,
        solver_reward=0.90,
        verifier_reward=0.10,
        claim_bond=0.10,
    )
    assert child.status == BountyLifecycle.ACTIVATION_BLOCKED
    assert child.verifier_id == "canonical-child-v1"
    assert child.parent_bounty_id == parent_id
    assert child.parent_round == 493
    assert "[REDACTED_EMAIL]" in child.sanitized_description

    # 2. Deposit pooled funding (0.50 + 0.50 = 1.00 USDC)
    res_partial = engine.deposit_pooled_funding(
        child.child_bounty_id, funder="0xFunderA", amount=0.50, tx_hash="0xTxA"
    )
    assert not res_partial["funded"]
    assert child.status == BountyLifecycle.ACTIVATION_BLOCKED

    res_full = engine.deposit_pooled_funding(
        child.child_bounty_id, funder="0xFunderB", amount=0.50, tx_hash="0xTxB"
    )
    assert res_full["funded"]
    assert child.status == BountyLifecycle.CLAIMABLE_LIVE

    # 3. Anti-self-claim verification
    with pytest.raises(ValueError, match="cannot self-claim"):
        engine.claim_child_bounty(child.child_bounty_id, solver_wallet=creator, bond_amount=0.10)

    with pytest.raises(ValueError, match="cannot self-claim"):
        engine.claim_child_bounty(child.child_bounty_id, solver_wallet=external_requester, bond_amount=0.10)

    # 4. Independent solver claim
    claim_res = engine.claim_child_bounty(
        child.child_bounty_id, solver_wallet=independent_solver, bond_amount=0.10
    )
    assert claim_res["status"] == BountyLifecycle.EXCLUSIVE_CLAIM
    assert child.current_claimant == independent_solver

    # 5. Non-claimant submission rejection
    unauthorized_proof = ChildBenchmarkProof(
        proof_uri="https://artifacts.solver.network/proof/493",
        artifact_hash="a" * 64,
        solver_wallet="0xEvilImposter",
        signature="0xSigValid",
    )
    with pytest.raises(PermissionError, match="Only active claimant"):
        engine.submit_and_settle(child.child_bounty_id, unauthorized_proof)

    # 6. Valid submission and canonical settlement
    valid_proof = ChildBenchmarkProof(
        proof_uri="https://artifacts.solver.network/proof/493",
        artifact_hash="b" * 64,
        solver_wallet=independent_solver,
        signature="0xSigSolver493",
        benchmark_metrics={"latency_ms": 12.4, "accuracy": 1.0},
    )
    settle_res = engine.submit_and_settle(child.child_bounty_id, valid_proof)
    assert settle_res["settled"] is True
    assert settle_res["status"] == BountyLifecycle.SETTLED
    assert settle_res["solver_payout_usdc"] == pytest.approx(1.00)  # 0.90 reward + 0.10 bond return
    assert settle_res["verifier_payout_usdc"] == pytest.approx(0.10)
    assert settle_res["parent_bounty_id"] == parent_id
    assert settle_res["parent_round"] == 493
    assert child.settlement_tx_hash.startswith("0x")


def test_invalid_proof_rejection():
    engine = CanonicalChildBountyEngine()
    child = engine.seed_canonical_child_bounty(
        creator="0xCreator",
        parent_bounty_id="0xParent493",
        parent_round=493,
        external_requester="0xRequester",
        work_title="Security Audit",
        raw_description="Audit task",
        category=ExternalWorkCategory.SECURITY_VERIFICATION,
    )
    engine.deposit_pooled_funding(child.child_bounty_id, "0xFunder", 1.00, "0xTx")
    engine.claim_child_bounty(child.child_bounty_id, "0xSolver", 0.10)

    # Insecure proof URI (http instead of https/ipfs)
    insecure_proof = ChildBenchmarkProof(
        proof_uri="http://insecure.site/proof",
        artifact_hash="c" * 64,
        solver_wallet="0xSolver",
        signature="0xSig",
    )
    res = engine.submit_and_settle(child.child_bounty_id, insecure_proof)
    assert res["settled"] is False
    assert res["status"] == BountyLifecycle.REJECTED
    assert "Proof URI must be secure" in res["error"]
