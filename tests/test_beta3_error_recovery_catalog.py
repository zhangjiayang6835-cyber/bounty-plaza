"""Unit test suite for Machine-Readable Beta3 Error Recovery Catalog Generator and Deterministic Validator.
Tests Issue #833 requirements:
- Validates all 19 deterministic predicates with score threshold 19/19.
- Verifies maximum bytes limit (maximum 131072 bytes).
- Verifies prohibition of localhost.
- Tests presence of all 12 exact error codes in order.
- Tests mapping to canonical settlement proof CompetitionSettledV2.
- Tests validation failures on invalid schema or corrupted codes.
"""

import json
import pytest
from scripts.beta3_error_recovery_catalog import (
    generate_error_recovery_catalog,
    validate_catalog_bytes,
)


def test_generated_catalog_passes_all_19_deterministic_predicates():
    catalog = generate_error_recovery_catalog()
    raw_bytes = json.dumps(catalog, indent=2).encode("utf-8")

    passed, score, failures = validate_catalog_bytes(raw_bytes)
    assert passed is True
    assert score == 19
    assert len(failures) == 0


def test_catalog_fails_if_localhost_present():
    catalog = generate_error_recovery_catalog()
    catalog["errors"][0]["next_action"] = "Submit to http://localhost:8080/api"
    raw_bytes = json.dumps(catalog).encode("utf-8")

    passed, score, failures = validate_catalog_bytes(raw_bytes)
    assert passed is False
    assert "utf8_excludes localhost failed" in failures


def test_catalog_fails_if_error_code_missing_or_out_of_order():
    catalog = generate_error_recovery_catalog()
    # Modify code at index 4
    catalog["errors"][4]["code"] = "wrong_code"
    raw_bytes = json.dumps(catalog).encode("utf-8")

    passed, score, failures = validate_catalog_bytes(raw_bytes)
    assert passed is False
    assert any("errors/4/code mismatch" in f for f in failures)


def test_catalog_fails_if_less_than_12_errors():
    catalog = generate_error_recovery_catalog()
    catalog["errors"] = catalog["errors"][:10]
    raw_bytes = json.dumps(catalog).encode("utf-8")

    passed, score, failures = validate_catalog_bytes(raw_bytes)
    assert passed is False
    assert any("errors length < 12" in f for f in failures)


def test_catalog_fails_if_payload_exceeds_maximum_bytes():
    catalog = generate_error_recovery_catalog()
    catalog["padding"] = "Y" * 140000
    raw_bytes = json.dumps(catalog).encode("utf-8")

    passed, score, failures = validate_catalog_bytes(raw_bytes)
    assert passed is False
    assert any("maximum_bytes exceeded" in f for f in failures)


def test_catalog_fails_if_payment_evidence_incorrect():
    catalog = generate_error_recovery_catalog()
    catalog["payment_evidence"] = "LegacySettled"
    raw_bytes = json.dumps(catalog).encode("utf-8")

    passed, score, failures = validate_catalog_bytes(raw_bytes)
    assert passed is False
    assert "payment_evidence mismatch" in failures
