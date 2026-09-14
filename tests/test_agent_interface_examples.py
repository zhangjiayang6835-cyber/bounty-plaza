"""Unit test suite for Complete Agent Interface Examples Generator and Deterministic Validator.
Tests Issue #832 requirements:
- Validates all 16 deterministic predicates with score threshold 16/16.
- Verifies maximum bytes limit (maximum 131072 bytes).
- Verifies prohibition of localhost and 127.0.0.1.
- Tests presence of all 6 exact interfaces (api, mcp, cli, python, typescript, x402) in required order.
- Tests final_check == "CompetitionSettledV2".
- Tests minimum occurrence thresholds (>= 6) for 'quote_proof' and 'authorize_proof_relay'.
- Tests validation failures on corrupted interfaces, misordered entries, or missing required terms.
"""

import json
import pytest
from scripts.agent_interface_examples import (
    generate_agent_interface_examples,
    validate_interface_examples_bytes,
)


def test_generated_interface_examples_passes_all_16_deterministic_predicates():
    artifact = generate_agent_interface_examples()
    raw_bytes = json.dumps(artifact, indent=2).encode("utf-8")

    passed, score, failures = validate_interface_examples_bytes(raw_bytes)
    assert passed is True
    assert score == 16
    assert len(failures) == 0


def test_interface_examples_fails_if_localhost_or_127_0_0_1_present():
    artifact = generate_agent_interface_examples()
    artifact["examples"][0]["entrypoint"] = "http://localhost:8000/inventory"
    raw_bytes = json.dumps(artifact).encode("utf-8")

    passed, score, failures = validate_interface_examples_bytes(raw_bytes)
    assert passed is False
    assert "utf8_excludes localhost failed" in failures

    artifact2 = generate_agent_interface_examples()
    artifact2["examples"][0]["entrypoint"] = "http://127.0.0.1:8000/inventory"
    raw_bytes2 = json.dumps(artifact2).encode("utf-8")

    passed2, score2, failures2 = validate_interface_examples_bytes(raw_bytes2)
    assert passed2 is False
    assert "utf8_excludes 127.0.0.1 failed" in failures2


def test_interface_examples_fails_if_interface_missing_or_misordered():
    artifact = generate_agent_interface_examples()
    # Swap two interfaces
    artifact["examples"][0]["interface"] = "mcp"
    artifact["examples"][1]["interface"] = "api"
    raw_bytes = json.dumps(artifact).encode("utf-8")

    passed, score, failures = validate_interface_examples_bytes(raw_bytes)
    assert passed is False
    assert any("examples/0/interface mismatch" in f for f in failures)


def test_interface_examples_fails_if_count_under_6():
    artifact = generate_agent_interface_examples()
    artifact["examples"] = artifact["examples"][:4]
    raw_bytes = json.dumps(artifact).encode("utf-8")

    passed, score, failures = validate_interface_examples_bytes(raw_bytes)
    assert passed is False
    assert any("examples length < 6" in f for f in failures)


def test_interface_examples_fails_if_quote_proof_under_6():
    artifact = generate_agent_interface_examples()
    # Replace one quote_proof occurrence
    raw_text = json.dumps(artifact)
    raw_text = raw_text.replace("quote_proof", "request_proof", 2)
    raw_bytes = raw_text.encode("utf-8")

    passed, score, failures = validate_interface_examples_bytes(raw_bytes)
    assert passed is False
    assert any("quote_proof count < 6" in f for f in failures)


def test_interface_examples_fails_if_authorize_proof_relay_under_6():
    artifact = generate_agent_interface_examples()
    raw_text = json.dumps(artifact)
    raw_text = raw_text.replace("authorize_proof_relay", "sign_relay", 2)
    raw_bytes = raw_text.encode("utf-8")

    passed, score, failures = validate_interface_examples_bytes(raw_bytes)
    assert passed is False
    assert any("authorize_proof_relay count < 6" in f for f in failures)


def test_interface_examples_fails_if_final_check_incorrect():
    artifact = generate_agent_interface_examples()
    artifact["final_check"] = "SafeBlockConfirmed"
    raw_bytes = json.dumps(artifact).encode("utf-8")

    passed, score, failures = validate_interface_examples_bytes(raw_bytes)
    assert passed is False
    assert "final_check mismatch" in failures


def test_interface_examples_fails_if_payload_exceeds_maximum_bytes():
    artifact = generate_agent_interface_examples()
    artifact["padding"] = "P" * 140000
    raw_bytes = json.dumps(artifact).encode("utf-8")

    passed, score, failures = validate_interface_examples_bytes(raw_bytes)
    assert passed is False
    assert any("maximum_bytes exceeded" in f for f in failures)
