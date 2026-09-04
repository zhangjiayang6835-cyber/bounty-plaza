"""Unit test suite for 25-Case AI Agent Findability and Task-Search Corpus.
Tests Issue #831 requirements:
- Validates all 19 deterministic predicates with score threshold 19/19.
- Verifies maximum bytes limit (maximum 196608 bytes).
- Verifies exclusion of localhost and 127.0.0.1.
- Tests presence and exact order of all 6 required labels.
- Tests presence of at least 25 structured test cases.
- Tests minimum occurrence counts (>= 5) for 'net_prize_if_win', 'coding', and 'AI agent'.
- Tests validation failures on corrupted schema, missing labels, or truncated case lists.
"""

import json
import pytest
from scripts.agent_findability_corpus import (
    generate_findability_corpus,
    validate_corpus_bytes,
)


def test_generated_corpus_passes_all_19_deterministic_predicates():
    corpus = generate_findability_corpus()
    raw_bytes = json.dumps(corpus, indent=2).encode("utf-8")

    passed, score, failures = validate_corpus_bytes(raw_bytes)
    assert passed is True
    assert score == 19
    assert len(failures) == 0


def test_corpus_fails_if_localhost_or_127_0_0_1_present():
    corpus = generate_findability_corpus()
    corpus["cases"][0]["route"] = "http://localhost:8000/inventory"
    raw_bytes = json.dumps(corpus).encode("utf-8")

    passed, score, failures = validate_corpus_bytes(raw_bytes)
    assert passed is False
    assert "utf8_excludes localhost failed" in failures

    corpus2 = generate_findability_corpus()
    corpus2["cases"][0]["route"] = "http://127.0.0.1:8000/inventory"
    raw_bytes2 = json.dumps(corpus2).encode("utf-8")

    passed2, score2, failures2 = validate_corpus_bytes(raw_bytes2)
    assert passed2 is False
    assert "utf8_excludes 127.0.0.1 failed" in failures2


def test_corpus_fails_if_required_label_missing_or_misordered():
    corpus = generate_findability_corpus()
    # Swap two labels
    corpus["required_labels"][0] = "ai-agent-welcome"
    corpus["required_labels"][1] = "bounty"
    raw_bytes = json.dumps(corpus).encode("utf-8")

    passed, score, failures = validate_corpus_bytes(raw_bytes)
    assert passed is False
    assert any("required_labels/0 mismatch" in f for f in failures)


def test_corpus_fails_if_cases_count_under_25():
    corpus = generate_findability_corpus()
    corpus["cases"] = corpus["cases"][:20]
    raw_bytes = json.dumps(corpus).encode("utf-8")

    passed, score, failures = validate_corpus_bytes(raw_bytes)
    assert passed is False
    assert any("cases length < 25" in f for f in failures)


def test_corpus_fails_if_keyword_occurrences_under_5():
    corpus = generate_findability_corpus()
    # Replace occurrences of coding
    raw_text = json.dumps(corpus).replace("coding", "programming")
    raw_bytes = raw_text.encode("utf-8")

    passed, score, failures = validate_corpus_bytes(raw_bytes)
    assert passed is False
    assert any("coding count < 5" in f for f in failures)


def test_corpus_fails_if_payload_exceeds_maximum_bytes():
    corpus = generate_findability_corpus()
    corpus["padding"] = "W" * 210000
    raw_bytes = json.dumps(corpus).encode("utf-8")

    passed, score, failures = validate_corpus_bytes(raw_bytes)
    assert passed is False
    assert any("maximum_bytes exceeded" in f for f in failures)
