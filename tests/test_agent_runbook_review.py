"""Unit tests for Adversarial Auditor & Byte Minimization Review Engine (Issue #841 - $89 USD)."""

import pytest
from scripts.agent_runbook_review import (
    RunbookAdversarialReviewer,
    generate_shortest_valid_runbook,
    SCHEMA_VERSION,
    TASK_ID,
    PAYMENT_EVIDENCE,
    DEFAULT_CTA,
    CANONICAL_INVENTORY_URL,
    CANONICAL_MCP_URL,
)


def test_shortest_runbook_audit_passes_all_18_predicates():
    reviewer = RunbookAdversarialReviewer()
    audit = reviewer.audit_all_predicates()

    assert audit["passed"] is True
    assert audit["total_checks"] == 18
    assert audit["passed_count"] == 18
    assert len(audit["failed_checks"]) == 0
    assert audit["byte_size_compact"] < 1024  # Highly optimized under 1KB
    assert audit["sha256"] is not None


def test_byte_efficiency_metrics():
    reviewer = RunbookAdversarialReviewer()
    eff = reviewer.measure_byte_efficiency()

    assert eff["compact_bytes"] < 1024
    assert eff["budget_used_pct"] < 1.0  # < 1% of 98304 bytes
    assert eff["efficiency_rating"] == "OPTIMAL (< 1KB)"


def test_review_report_generation():
    reviewer = RunbookAdversarialReviewer()
    report = reviewer.generate_review_report()

    assert report["review_status"] == "APPROVED"
    assert report["target_task"] == TASK_ID
    assert report["audit_results"]["passed"] is True
    assert len(report["findings"]) >= 5
    assert report["verified_artifact"]["payment_evidence"] == PAYMENT_EVIDENCE


def test_audit_detects_tampered_runbooks():
    reviewer = RunbookAdversarialReviewer()
    tampered = generate_shortest_valid_runbook()

    # Tamper with localhost injection
    tampered["steps"][0]["entrypoint"] = "http://localhost:8080"
    audit1 = reviewer.audit_all_predicates(tampered)
    assert audit1["passed"] is False
    assert "utf8_excludes_localhost" in audit1["failed_checks"]

    # Tamper with missing payment evidence
    tampered2 = generate_shortest_valid_runbook()
    tampered2["payment_evidence"] = "UnverifiedSettlement"
    audit2 = reviewer.audit_all_predicates(tampered2)
    assert audit2["passed"] is False
    assert "payment_evidence_match" in audit2["failed_checks"]
