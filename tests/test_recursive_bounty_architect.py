"""Unit tests for Recursive Bounty Architect – Five-Fold Esoteric Expansion Protocol.
Resolves Issue #645: [BOUNTY] [$10000] [AGENTIC] [AI] Recursive Bounty Architect – Five-Fold Esoteric Expansion Protocol for SS13.
Upstream Reference: Iamgoofball/-tg-station#147.
"""

import pytest
from scripts.recursive_bounty_architect import (
    RecursiveBountyArchitect,
    EsotericBountyListing,
    ESOTERIC_DOMAINS,
    OPIR_BASE_PREAMBLE,
)


@pytest.fixture
def architect():
    return RecursiveBountyArchitect()


def test_domain_specification_count(architect):
    assert len(architect.domains) == 5
    expected_tags = {"DYSON", "ANOMALIES", "MULTIVERSE", "CHRONO", "MEMETICS"}
    actual_tags = {d["tag"] for d in architect.domains}
    assert expected_tags == actual_tags


def test_verbatim_preamble_integrity(architect):
    assert "📌 Overview" in architect.preamble
    assert "Unreal Engine 5" in architect.preamble
    assert "Opire, an agentic task marketplace" in architect.preamble
    assert "Total bounty: $10,000" in architect.preamble
    assert "KYD" in architect.preamble


def test_bounty_listing_generation_structure(architect):
    bounties = architect.generate_all_five_bounties()
    assert len(bounties) == 5

    for b in bounties:
        assert isinstance(b, EsotericBountyListing)
        assert b.tag in {"DYSON", "ANOMALIES", "MULTIVERSE", "CHRONO", "MEMETICS"}
        assert "[BOUNTY]" in b.title
        assert "🎯 Objective" in b.markdown_content
        assert "### Required Subsystems & Technical Deliverables:" in b.markdown_content
        assert "### Acceptance Criteria:" in b.markdown_content
        assert "Opire Singularity Council" in b.markdown_content


def test_bounty_validation_compliance(architect):
    bounties = architect.generate_all_five_bounties()

    for b in bounties:
        val_report = architect.validate_bounty_listing(b)
        assert val_report["is_valid"] is True
        assert val_report["status"] == "VALIDATED_COMPLIANT"
        assert val_report["has_verbatim_preamble"] is True
        assert val_report["has_objective"] is True
        assert val_report["has_subsystems"] is True
        assert val_report["has_acceptance_criteria"] is True
        assert val_report["word_count"] > 150


def test_export_all_to_dict_payload(architect):
    payload = architect.export_all_to_dict()
    assert payload["total_bounties"] == 5
    assert len(payload["bounties"]) == 5
    assert payload["protocol"] == "Five-Fold Esoteric Expansion Protocol for SS13"
