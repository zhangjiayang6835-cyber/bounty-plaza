"""Tests for external-user-request child bounty seeding and settlement engine.
Validates Issue #499 resolution for NSPG13/agent-bounties#220 / Base Mainnet (EIP-155:8453 autonomous-v1).
"""

import pytest
import sys
from pathlib import Path

# Add bounty-plaza root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.seed_external_request_child_bounty import (
    ExternalRequestEngine,
    ExternalRequestCategory,
    DigitalDeliverablePayload,
    BountyLifecycle,
)


def test_seed_and_co_funding_with_redaction():
    engine = ExternalRequestEngine()
    raw_desc = "Integrate our webhook with contact alice@corp.example and secret api_key=secret_1234567890abcdef. Call +1-555-123-4567."
    bounty = engine.seed_external_bounty(
        creator="0xCreatorWallet111",
        external_requester="0xExternalClient222",
        raw_title="Webhook Relay Integration",
        raw_description=raw_desc,
        category=ExternalRequestCategory.API_INTEGRATION,
        solver_reward=0.90,
        verifier_reward=0.10,
        claim_bond=0.10,
    )

    # Verify PII redaction
    assert "alice@corp.example" not in bounty.sanitized_description
    assert "[REDACTED_EMAIL]" in bounty.sanitized_description
    assert "secret_1234567890abcdef" not in bounty.sanitized_description
    assert "[REDACTED_SECRET]" in bounty.sanitized_description
    assert bounty.status == BountyLifecycle.ACTIVATION_BLOCKED

    # Co-funding from third-party pool
    res_co1 = engine.add_co_funding(bounty.bounty_id, "0xSponsorA", 0.60, "0xTxSponsorA")
    assert not res_co1["is_claimable"]
    assert bounty.status == BountyLifecycle.ACTIVATION_BLOCKED

    res_co2 = engine.add_co_funding(bounty.bounty_id, "0xSponsorB", 0.40, "0xTxSponsorB")
    assert res_co2["is_claimable"]
    assert bounty.status == BountyLifecycle.CLAIMABLE_LIVE
    assert bounty.current_funding_usdc == 1.00


def test_claim_anti_self_claim_rules():
    engine = ExternalRequestEngine()
    bounty = engine.seed_external_bounty(
        creator="0xCreatorWallet333",
        external_requester="0xClientWallet333",
        raw_title="Data Normalization Task",
        raw_description="Normalize CSV outputs",
        category=ExternalRequestCategory.DATA_NORMALIZATION,
    )
    engine.add_co_funding(bounty.bounty_id, "0xCreatorWallet333", 1.00, "0xFundTx")

    # Creator self-claim check
    with pytest.raises(ValueError, match="cannot self-claim"):
        engine.claim_bounty(bounty.bounty_id, "0xCreatorWallet333", 0.10)

    # External requester self-claim check
    with pytest.raises(ValueError, match="cannot self-claim"):
        engine.claim_bounty(bounty.bounty_id, "0xClientWallet333", 0.10)

    # Insufficient bond check
    with pytest.raises(ValueError, match="Bond 0.05 below required"):
        engine.claim_bounty(bounty.bounty_id, "0xIndependentSolver444", 0.05)

    # Valid independent claim
    claim_res = engine.claim_bounty(bounty.bounty_id, "0xIndependentSolver444", 0.10)
    assert claim_res["status"] == BountyLifecycle.EXCLUSIVE_CLAIM.value
    assert claim_res["claimant"] == "0xIndependentSolver444"


def test_submission_deliverable_verification_and_settlement():
    engine = ExternalRequestEngine()
    bounty = engine.seed_external_bounty(
        creator="0xCreatorWallet555",
        external_requester="0xClientWallet555",
        raw_title="Security Audit on Gate",
        raw_description="Check replay attack invariants",
        category=ExternalRequestCategory.SECURITY_AUDIT,
    )
    engine.add_co_funding(bounty.bounty_id, "0xCoFunder", 1.00, "0xFundTx555")
    engine.claim_bounty(bounty.bounty_id, "0xAuditorSolver666", 0.10)

    payload = DigitalDeliverablePayload(
        deliverable_uri="https://github.com/org/repo/pull/42",
        artifact_hash="0xabcdef1234567890abcdef1234567890abcdef12",
        solver_wallet="0xAuditorSolver666",
        signature="0xsig666",
        metrics={"tests_added": 12, "vulns_patched": 2},
    )

    settle_res = engine.submit_and_settle(bounty.bounty_id, payload)
    assert settle_res["status"] == BountyLifecycle.SETTLED.value
    assert settle_res["settled"] is True
    assert settle_res["solver_payout_usdc"] == 1.00  # 0.90 reward + 0.10 bond returned
    assert settle_res["verifier_payout_usdc"] == 0.10
    assert bounty.settlement_tx_hash is not None


def test_invalid_deliverable_rejection():
    engine = ExternalRequestEngine()
    bounty = engine.seed_external_bounty(
        creator="0xCreatorWallet777",
        external_requester="0xClientWallet777",
        raw_title="Doc Automation",
        raw_description="Generate sphinx docs",
        category=ExternalRequestCategory.DOC_AUTOMATION,
    )
    engine.add_co_funding(bounty.bounty_id, "0xCreatorWallet777", 1.00, "0xFundTx777")
    engine.claim_bounty(bounty.bounty_id, "0xSolver777", 0.10)

    # Insecure URI deliverable
    bad_payload = DigitalDeliverablePayload(
        deliverable_uri="http://insecure-http-site.com/file.tar",
        artifact_hash="short",
        solver_wallet="0xSolver777",
        signature="",
    )

    res = engine.submit_and_settle(bounty.bounty_id, bad_payload)
    assert res["status"] == BountyLifecycle.REJECTED.value
    assert res["settled"] is False
    assert "Deliverable URI must be secure" in res["error"]
