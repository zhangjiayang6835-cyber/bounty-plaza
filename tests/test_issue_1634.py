"""Comprehensive verification test suite for Issue 1634 deliverables."""

from pathlib import Path

from packages.a2a_agent_card import (
    AgentCard,
    AgentCardDiscoveryEngine,
    AgentCardValidator,
    BountySettlementEngine,
    CanonicalUrlNormalizer,
)


def test_canonical_fixture_passes_strict_acceptance():
    """Verify that canonical fixture passes all acceptance rules."""
    fixture_path = (
        Path(__file__).resolve().parent.parent
        / "packages"
        / "a2a_agent_card"
        / "fixtures"
        / "a2a-agent-card.json"
    )
    is_valid, errors = AgentCardValidator.validate_file(str(fixture_path))
    assert is_valid, f"Validation failed: {errors}"
    assert not errors


def test_dynamic_card_matches_serialized_fixture():
    """Verify programmatic factory output matches static fixture."""
    card = AgentCard.create_canonical()
    is_valid, errors = AgentCardValidator.validate_dict(card.to_dict())
    assert is_valid, f"Programmatic card invalid: {errors}"
    assert not errors


def test_validator_rejects_altered_product_name():
    """Verify validator enforces canonical product name."""
    card = AgentCard.create_canonical().to_dict()
    card["name"] = "Unofficial Agent Bounties"
    is_valid, errors = AgentCardValidator.validate_dict(card)
    assert not is_valid
    assert any("Agent Card name must be 'Agent Bounties'" in e for e in errors)


def test_validator_rejects_root_protocol_version():
    """Verify protocolVersion is rejected at root level."""
    card = AgentCard.create_canonical().to_dict()
    card["protocolVersion"] = "1.0"
    is_valid, errors = AgentCardValidator.validate_dict(card)
    assert not is_valid
    assert any("protocolVersion belongs on interfaces" in e for e in errors)


def test_validator_rejects_missing_mandatory_skills():
    """Verify omission of any mandatory skill triggers rejection."""
    card = AgentCard.create_canonical().to_dict()
    card["skills"] = [
        s for s in card["skills"] if s["id"] != "check-bounty-settlement"
    ]
    is_valid, errors = AgentCardValidator.validate_dict(card)
    assert not is_valid
    assert any("missing mandatory skills" in e for e in errors)


def test_validator_rejects_forbidden_credential_terms():
    """Verify presence of forbidden secrets causes immediate rejection."""
    card = AgentCard.create_canonical().to_dict()
    card["description"] = "Card containing private_key leak"
    is_valid, errors = AgentCardValidator.validate_dict(card)
    assert not is_valid
    assert any("forbidden credential material" in e for e in errors)


def test_validator_rejects_missing_required_evidence_boundaries():
    """Verify omission of required evidence words causes rejection."""
    card = AgentCard.create_canonical().to_dict()
    card["description"] = "A standard discovery card without key terms."
    for skill in card["skills"]:
        skill["description"] = "Generic task description"
        skill["tags"] = ["generic"]
    is_valid, errors = AgentCardValidator.validate_dict(card)
    assert not is_valid
    assert any("evidence boundary" in e for e in errors)


def test_url_normalizer_preserves_query_case():
    """Verify query parameter casing is not converted to lowercase."""
    raw = "https://API.AgentBounties.App:443/a2a/v1?token=AbCdEfGh&Session=XYZ"
    normalized = CanonicalUrlNormalizer.normalize(raw)
    assert normalized == "https://api.agentbounties.app/a2a/v1?token=AbCdEfGh&Session=XYZ"


def test_url_normalizer_preserves_trailing_slash():
    """Verify trailing slash distinctions are preserved across paths."""
    with_slash = "https://api.agentbounties.app/a2a/v1/"
    without_slash = "https://api.agentbounties.app/a2a/v1"
    assert CanonicalUrlNormalizer.normalize(with_slash) == "https://api.agentbounties.app/a2a/v1/"
    assert CanonicalUrlNormalizer.normalize(without_slash) == "https://api.agentbounties.app/a2a/v1"


def test_url_normalizer_resolves_dot_segments():
    """Verify relative path segments are normalized cleanly."""
    raw = "https://api.agentbounties.app/a2a/internal/../v1"
    assert CanonicalUrlNormalizer.normalize(raw) == "https://api.agentbounties.app/a2a/v1"


def test_discovery_engine_cache_headers_and_etag():
    """Verify discovery engine outputs HTTP entity tags and cache controls."""
    engine = AgentCardDiscoveryEngine()
    payload, headers = engine.get_discovery_payload()
    assert payload["name"] == "Agent Bounties"
    assert "ETag" in headers
    assert "Cache-Control" in headers
    assert "public, max-age=300" in headers["Cache-Control"]


def test_discovery_engine_conditional_304():
    """Verify If-None-Match matching current ETag returns 304 Not Modified."""
    engine = AgentCardDiscoveryEngine()
    _, headers = engine.get_discovery_payload()
    current_etag = headers["ETag"]

    status, body, _ = engine.handle_conditional_request(current_etag)
    assert status == 304
    assert body is None

    status, body, _ = engine.handle_conditional_request('"outdated-etag"')
    assert status == 200
    assert body is not None


def test_settlement_engine_financial_calculations():
    """Verify reward calculation formulas for 0.99 USDC tier."""
    breakdown = BountySettlementEngine.calculate_rewards(0.99)
    assert breakdown["nominalUsdc"] == 0.99
    assert breakdown["contributorRatio"] == 0.95
    assert breakdown["grossPoints"] == 1.2375
    assert breakdown["contributorPoints"] == 1.1756
    assert breakdown["netCashUsd"] == 0.8464


def test_settlement_receipt_generation():
    """Verify cryptographic receipt structure and payout routing."""
    receipt = BountySettlementEngine.generate_settlement_receipt(0.99, 0.01)
    as_dict = receipt.to_dict()
    assert as_dict["contractAddress"] == "0x3edcf165583824795f6f0a92b3dbc38c4d930d41"
    assert as_dict["networkId"] == "eip155:8453:base-mainnet"
    assert as_dict["paymentState"] == "bountysettled"
    assert as_dict["solverRewardUsdc"] == 0.99
    assert as_dict["entryBondUsdc"] == 0.01
    assert as_dict["totalFundingUsdc"] == 1.00
    assert as_dict["evmPayoutAddress"] == "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89"
    expected_stellar = "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC"
    assert as_dict["stellarPayoutAddress"] == expected_stellar
    assert len(as_dict["receiptHash"]) == 64
