"""Unit tests for Agent Earning Runbook Feature (Issue #837 - Open Competition V2)."""

import pytest
from scripts.agent_earning_runbook_feature import (
    AgentRunbookExecutionEngine,
    CANONICAL_SCHEMA_VERSION,
    CANONICAL_TASK_ID,
    CANONICAL_STEPS,
    CANONICAL_PAYMENT_EVIDENCE,
    CANONICAL_DEFAULT_CTA,
    CANONICAL_INVENTORY_URL,
    CANONICAL_MCP_URL,
)


def test_base_artifact_predicates_all_pass():
    engine = AgentRunbookExecutionEngine()
    predicates = engine.validate_base_predicates(engine.artifact)
    assert len(predicates) == 18
    for name, passed in predicates:
        assert passed is True, f"Predicate failed: {name}"


def test_step_idempotency_and_caching():
    engine = AgentRunbookExecutionEngine()
    # First execution
    res1 = engine.execute_step("inspect_profiles")
    assert res1["status"] == "COMPLETED"
    assert res1["cached"] is False
    assert res1["output_hash"] is not None

    # Repeated execution returns cached state without re-running
    res2 = engine.execute_step("inspect_profiles")
    assert res2["status"] == "COMPLETED"
    assert res2["cached"] is True
    assert res2["output_hash"] == res1["output_hash"]


def test_full_sequential_runbook_pipeline():
    engine = AgentRunbookExecutionEngine()
    full_run = engine.execute_full_runbook()
    assert full_run["status"] == "SUCCESS"
    assert full_run["completed_steps"] == 7
    assert full_run["payment_evidence"] == CANONICAL_PAYMENT_EVIDENCE
    assert full_run["total_gas_gwei"] == 0.10
    assert full_run["final_receipt_hash"] is not None


def test_crash_interruption_and_checkpoint_recovery():
    engine = AgentRunbookExecutionEngine()
    crash_res = engine.simulate_crash_and_resume(crash_at_step="quote_proof")
    assert crash_res["resumed"] is True
    assert crash_res["crash_point"] == "quote_proof"
    assert crash_res["final_status"] == "COMPLETED"
    assert crash_res["all_steps_verified"] is True


def test_rejection_of_invalid_or_missing_predicates():
    engine = AgentRunbookExecutionEngine()
    corrupt_artifact = engine.generate_base_artifact()
    corrupt_artifact["steps"] = corrupt_artifact["steps"][:5]  # Drop below 7 steps

    with pytest.raises(ValueError, match="steps_length_ge_7"):
        engine.validate_base_predicates(corrupt_artifact)

    corrupt_artifact2 = engine.generate_base_artifact()
    corrupt_artifact2["steps"][0]["entrypoint"] = "http://localhost:8080/mcp"
    with pytest.raises(ValueError, match="utf8_excludes_localhost"):
        engine.validate_base_predicates(corrupt_artifact2)
