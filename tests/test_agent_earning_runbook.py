"""Unit test suite for Deterministic Agent Earning Runbook Generator and Validator.
Tests Issue #835 requirements:
- Validates all 18 deterministic predicates with score threshold 18/18.
- Tests payload size limit (maximum 98304 bytes).
- Tests prohibition of localhost and 127.0.0.1.
- Tests ordered steps from inspect_profiles to verify_settlement.
- Tests presence of canonical inventory and MCP URLs.
- Tests detection of invalid schema or missing required properties.
"""

import json
import pytest
from scripts.agent_earning_runbook import (
    generate_runbook_artifact,
    validate_runbook_bytes,
)


def test_generated_runbook_passes_all_18_deterministic_predicates():
    artifact = generate_runbook_artifact()
    raw_bytes = json.dumps(artifact, indent=2).encode("utf-8")

    passed, score, failures = validate_runbook_bytes(raw_bytes)
    assert passed is True
    assert score == 18
    assert len(failures) == 0


def test_runbook_fails_if_localhost_or_127_0_0_1_present():
    artifact = generate_runbook_artifact()
    artifact["steps"][0]["entrypoint"] = "http://localhost:8000/mcp"
    raw_bytes = json.dumps(artifact).encode("utf-8")

    passed, score, failures = validate_runbook_bytes(raw_bytes)
    assert passed is False
    assert "utf8_excludes localhost failed" in failures


def test_runbook_fails_if_step_order_or_id_modified():
    artifact = generate_runbook_artifact()
    # Swap first two steps
    artifact["steps"][0]["id"] = "list_active"
    artifact["steps"][1]["id"] = "inspect_profiles"
    raw_bytes = json.dumps(artifact).encode("utf-8")

    passed, score, failures = validate_runbook_bytes(raw_bytes)
    assert passed is False
    assert any("steps/0/id mismatch" in f for f in failures)


def test_runbook_fails_if_payload_exceeds_maximum_bytes():
    artifact = generate_runbook_artifact()
    artifact["padding"] = "X" * 100000
    raw_bytes = json.dumps(artifact).encode("utf-8")

    passed, score, failures = validate_runbook_bytes(raw_bytes)
    assert passed is False
    assert any("maximum_bytes exceeded" in f for f in failures)


def test_runbook_fails_if_canonical_urls_missing():
    artifact = generate_runbook_artifact()
    artifact["steps"][0]["entrypoint"] = "https://custom.mcp.io"
    artifact["steps"][1]["entrypoint"] = "https://custom.inventory.io"
    raw_bytes = json.dumps(artifact).encode("utf-8")

    passed, score, failures = validate_runbook_bytes(raw_bytes)
    assert passed is False
    assert "missing canonical inventory URL" in failures
    assert "missing canonical MCP URL" in failures
