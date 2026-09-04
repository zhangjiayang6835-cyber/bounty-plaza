"""Unit tests for Agent Runbook Yield Orchestrator (Issue #838 - $89 USD)."""

import pytest
from scripts.agent_runbook_yield_orchestrator import (
    AgentRunbookYieldOrchestrator,
    BountyCandidate,
    SCHEMA_VERSION,
    TASK_ID,
    PAYMENT_EVIDENCE,
    DEFAULT_CTA,
    CANONICAL_INVENTORY_URL,
    CANONICAL_MCP_URL,
)


def test_yield_velocity_calculation_and_ranking():
    orchestrator = AgentRunbookYieldOrchestrator(min_margin_usdc=0.50)

    # Fast settling autonomous bounty: $0.99 reward, $0.05 gas/proof, 10s latency
    c1 = BountyCandidate(
        bounty_id="eip155:8453:autonomous:0x1",
        title="Fast SP1 Groth16 Verifier",
        reward_usdc=0.99,
        bond_required_usdc=0.01,
        estimated_gas_usd=0.04,
        proof_quote_usd=0.01,
        estimated_latency_seconds=10.0,
        verifier_type="deterministic_module",
        verifier_ready=True,
    )

    # High payout but slow manual review bounty: $500 reward, $5 gas, 86400s (24h) latency
    c2 = BountyCandidate(
        bounty_id="manual:github:0x2",
        title="Manual Review Feature",
        reward_usdc=500.0,
        bond_required_usdc=0.0,
        estimated_gas_usd=5.0,
        proof_quote_usd=0.0,
        estimated_latency_seconds=86400.0,
        verifier_type="human_council",
        verifier_ready=False,
    )

    # Medium fast bounty: $90 reward, $0.10 gas, 300s latency
    c3 = BountyCandidate(
        bounty_id="eip155:8453:autonomous:0x3",
        title="Wallet UX Child Bounty",
        reward_usdc=90.0,
        bond_required_usdc=0.10,
        estimated_gas_usd=0.08,
        proof_quote_usd=0.02,
        estimated_latency_seconds=300.0,
        verifier_type="deterministic_module",
        verifier_ready=True,
    )

    orchestrator.register_candidate(c1)
    orchestrator.register_candidate(c2)
    orchestrator.register_candidate(c3)

    # Fast payout filter ignores unready verifiers
    ranked_fast = orchestrator.rank_opportunities(fast_payout_only=True)
    assert len(ranked_fast) == 2
    # c3 net margin: 89.90 / 300s = ~0.2996/s
    # c1 net margin: 0.94 / 10s = ~0.094/s
    assert ranked_fast[0]["bounty_id"] == "eip155:8453:autonomous:0x3"
    assert ranked_fast[1]["bounty_id"] == "eip155:8453:autonomous:0x1"


def test_generated_runbook_artifact_meets_all_18_predicates():
    orchestrator = AgentRunbookYieldOrchestrator()
    artifact = orchestrator.generate_optimized_runbook("bounty-high-yield-001")

    predicates = orchestrator.verify_predicates(artifact)
    assert len(predicates) == 18
    for name, passed in predicates:
        assert passed is True, f"Predicate failed: {name}"

    assert artifact["schema_version"] == SCHEMA_VERSION
    assert artifact["task_id"] == TASK_ID
    assert artifact["payment_evidence"] == PAYMENT_EVIDENCE
    assert artifact["default_cta"] == DEFAULT_CTA
    assert len(artifact["steps"]) == 7


def test_predicate_rejection_on_tampered_artifact():
    orchestrator = AgentRunbookYieldOrchestrator()
    artifact = orchestrator.generate_optimized_runbook()

    # Corrupt schema version
    artifact["schema_version"] = "invalid/v2"
    with pytest.raises(ValueError, match="schema_version_match"):
        orchestrator.verify_predicates(artifact)

    # Re-generate and corrupt localhost inclusion
    artifact2 = orchestrator.generate_optimized_runbook()
    artifact2["steps"][1]["entrypoint"] = "http://localhost:3000/inventory"
    with pytest.raises(ValueError, match="utf8_excludes_localhost"):
        orchestrator.verify_predicates(artifact2)
