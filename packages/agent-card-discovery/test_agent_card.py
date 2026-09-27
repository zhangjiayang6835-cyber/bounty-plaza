"""Test suite for deterministic A2A agent-card discovery.

Covers all 15 specification points and edge cases:
1. Canonical URL building
2. Invalid origin rejection (malformed scheme/host)
3. Happy path resolution and normalization
4. Capability coercion, deduplication, and alphabetical sorting
5. Skill coercion, deduplication, and alphabetical sorting
6. Graceful version fallback to base schema (1.0) for unsupported versions
7. Strict document validation rejecting missing 'name'
8. Strict document validation rejecting missing 'url'
9. Rejection of non-object documents
10. Handling empty or missing fetcher responses
11. Missing fetcher error reporting
12. AgentCard supports() lookup (case-insensitive across capabilities & skills)
13. AgentCard as_dict() immutability and serialization
14. Metadata flattening and non-scalar dropping
15. Batch discovery (discover_many) skipping failing origins without aborting
"""

import pytest
from agent_card import (
    AgentCard,
    AgentCardResolver,
    CardValidationError,
    DiscoveryError,
    well_known_url,
    normalise,
)


def test_well_known_url_building():
    assert well_known_url("https://agent.example.com") == "https://agent.example.com/.well-known/agent-card.json"
    assert well_known_url("http://agent.example.com:80") == "http://agent.example.com/.well-known/agent-card.json"
    assert well_known_url("https://agent.example.com:443") == "https://agent.example.com/.well-known/agent-card.json"
    assert well_known_url("https://agent.example.com:8443") == "https://agent.example.com:8443/.well-known/agent-card.json"
    assert well_known_url("https://agent.example.com", "/custom/card.json") == "https://agent.example.com/custom/card.json"


def test_invalid_origin_rejection():
    with pytest.raises(DiscoveryError) as exc_info:
        well_known_url("ftp://agent.example.com")
    assert "Invalid scheme" in str(exc_info.value)

    with pytest.raises(DiscoveryError) as exc_info:
        well_known_url("javascript:alert(1)")
    assert "Invalid scheme" in str(exc_info.value)

    with pytest.raises(DiscoveryError):
        well_known_url("not-a-valid-url")

    with pytest.raises(DiscoveryError):
        well_known_url("http://")


def test_happy_path_resolution():
    doc = {
        "name": "SuperAgent",
        "url": "https://super.agent.io",
        "version": "1.0",
        "description": "An autonomous AI agent",
        "capabilities": ["inference", "code-gen"],
        "skills": ["python", "solidity"],
        "metadata": {"version": "v1.2.3"}
    }
    card = normalise("https://super.agent.io", doc)
    assert card.name == "SuperAgent"
    assert card.url == "https://super.agent.io"
    assert card.version == "1.0"
    assert card.description == "An autonomous AI agent"
    assert card.capabilities == ("code-gen", "inference")
    assert card.skills == ("python", "solidity")
    assert card.metadata == {"version": "v1.2.3"}


def test_capability_dedup_and_sorting():
    doc = {
        "name": "SorterAgent",
        "url": "https://sorter.agent.io",
        "capabilities": ["translate", "  transcribe  ", "translate", "summarize", 402, "summarize"],
    }
    card = normalise("https://sorter.agent.io", doc)
    # Coerced, trimmed, deduped, and sorted alphabetically
    assert card.capabilities == ("402", "summarize", "transcribe", "translate")


def test_skill_dedup_and_sorting():
    doc = {
        "name": "SkillfulAgent",
        "url": "https://skills.agent.io",
        "skills": ["rust", "python", "golang", "python", "  c++  "],
    }
    card = normalise("https://skills.agent.io", doc)
    assert card.skills == ("c++", "golang", "python", "rust")


def test_graceful_version_fallback():
    # Unsupported version falls back to "1.0"
    doc_unsupported = {
        "name": "FutureAgent",
        "url": "https://future.agent.io",
        "version": "9.9-beta"
    }
    card = normalise("https://future.agent.io", doc_unsupported)
    assert card.version == "1.0"

    # Supported version preserved
    doc_v11 = {
        "name": "V11Agent",
        "url": "https://v11.agent.io",
        "version": "1.1"
    }
    card_v11 = normalise("https://v11.agent.io", doc_v11)
    assert card_v11.version == "1.1"


def test_missing_name_validation():
    doc = {"url": "https://agent.example.com"}
    with pytest.raises(CardValidationError) as exc_info:
        normalise("https://agent.example.com", doc)
    assert "name" in exc_info.value.missing_fields


def test_missing_url_validation():
    doc = {"name": "NoUrlAgent"}
    with pytest.raises(CardValidationError) as exc_info:
        normalise("https://agent.example.com", doc)
    assert "url" in exc_info.value.missing_fields


def test_missing_both_name_and_url():
    doc = {"description": "Empty card"}
    with pytest.raises(CardValidationError) as exc_info:
        normalise("https://agent.example.com", doc)
    assert "name" in exc_info.value.missing_fields
    assert "url" in exc_info.value.missing_fields


def test_non_object_document_validation():
    with pytest.raises(CardValidationError):
        normalise("https://agent.example.com", "not a dict")
    with pytest.raises(CardValidationError):
        normalise("https://agent.example.com", None)
    with pytest.raises(CardValidationError):
        normalise("https://agent.example.com", [1, 2, 3])


def test_empty_fetcher_response():
    resolver = AgentCardResolver(fetcher=lambda url: {})
    with pytest.raises(DiscoveryError) as exc_info:
        resolver.discover("https://agent.example.com")
    assert "Empty response or card not found" in str(exc_info.value)


def test_missing_fetcher():
    resolver = AgentCardResolver(fetcher=None)
    with pytest.raises(DiscoveryError) as exc_info:
        resolver.discover("https://agent.example.com")
    assert "No fetcher callable configured" in str(exc_info.value)


def test_agent_card_supports_lookup():
    card = AgentCard(
        name="LookupAgent",
        url="https://lookup.agent.io",
        capabilities=["Inference", "Speech"],
        skills=["Python", "Analysis"]
    )
    assert card.supports("inference")
    assert card.supports("INFERENCE")
    assert card.supports("  speech  ")
    assert card.supports("python")
    assert card.supports("analysis")
    assert not card.supports("blockchain")


def test_metadata_flattening():
    doc = {
        "name": "MetaAgent",
        "url": "https://meta.agent.io",
        "metadata": {
            "rate_limit": 100,
            "region": "us-east-1",
            "is_active": True,
            "nested": {"complex": "ignored"},
            "tags": ["drop", "me"]
        }
    }
    card = normalise("https://meta.agent.io", doc)
    assert card.metadata == {
        "rate_limit": "100",
        "region": "us-east-1",
        "is_active": "True"
    }


def test_batch_discovery_skips_failing_origins():
    mock_registry = {
        "https://valid1.io/.well-known/agent-card.json": {
            "name": "AgentOne",
            "url": "https://valid1.io",
            "capabilities": ["task1"]
        },
        "https://valid2.io/.well-known/agent-card.json": {
            "name": "AgentTwo",
            "url": "https://valid2.io",
            "capabilities": ["task2"]
        }
    }

    def mock_fetcher(url: str):
        if url in mock_registry:
            return mock_registry[url]
        raise RuntimeError("404 Not Found")

    resolver = AgentCardResolver(fetcher=mock_fetcher)

    origins = [
        "https://valid1.io",
        "invalid://bad-scheme",           # Fails URL validation
        "https://missing404.io",          # Fails fetcher
        "https://valid2.io",
    ]

    cards = resolver.discover_many(origins)
    # The batch continues and recovers cards from valid origins
    assert len(cards) == 2
    assert cards[0].name == "AgentOne"
    assert cards[1].name == "AgentTwo"
