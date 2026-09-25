"""Tests for the deterministic A2A agent-card discovery resolver."""

from __future__ import annotations

from typing import Dict, Optional

import pytest

from agent_card import (
    SUPPORTED_VERSIONS,
    WELL_KNOWN_PATH,
    AgentCard,
    AgentCardResolver,
    CardValidationError,
    DiscoveryError,
)


def resolver_for(documents: Dict[str, Optional[Dict[str, object]]]) -> AgentCardResolver:
    """Build a resolver whose fetcher reads from ``documents``."""
    return AgentCardResolver(lambda url: documents.get(url))


def test_well_known_url_is_canonical() -> None:
    """The well-known URL keeps scheme and host and appends the fixed path."""
    resolver = resolver_for({})
    assert resolver.well_known_url("https://agent.example") == \
        "https://agent.example" + WELL_KNOWN_PATH
    assert resolver.well_known_url("http://agent.example:8080/") == \
        "http://agent.example:8080" + WELL_KNOWN_PATH


def test_well_known_url_rejects_bad_origin() -> None:
    """Origins without a usable scheme/host are rejected."""
    resolver = resolver_for({})
    with pytest.raises(DiscoveryError):
        resolver.well_known_url("not-a-url")


def test_discover_returns_normalised_card() -> None:
    """A valid document is parsed into an AgentCard."""
    url = "https://agent.example" + WELL_KNOWN_PATH
    resolver = resolver_for({
        url: {
            "name": "agent",
            "version": "1.1",
            "url": "https://agent.example",
            "capabilities": ["tasks", "streaming"],
            "skills": ["translate"],
        }
    })
    card = resolver.discover("https://agent.example")
    assert card.name == "agent"
    assert card.version == "1.1"
    assert card.capabilities == ("streaming", "tasks")


def test_capabilities_are_sorted_and_deduplicated() -> None:
    """Capability lists are normalised to a stable sorted tuple."""
    card = AgentCardResolver.normalise({
        "name": "agent",
        "url": "https://agent.example",
        "capabilities": ["b", "a", "b"],
    })
    assert card.capabilities == ("a", "b")


def test_unknown_version_falls_back() -> None:
    """An unsupported version falls back to the first supported one."""
    card = AgentCardResolver.normalise({
        "name": "agent",
        "url": "https://agent.example",
        "version": "9.9",
    })
    assert card.version == SUPPORTED_VERSIONS[0]


def test_missing_name_is_rejected() -> None:
    """A document without a name raises CardValidationError."""
    with pytest.raises(CardValidationError) as excinfo:
        AgentCardResolver.normalise({"url": "https://agent.example"})
    assert "name" in excinfo.value.missing


def test_missing_url_is_rejected() -> None:
    """A document without a url raises CardValidationError."""
    with pytest.raises(CardValidationError) as excinfo:
        AgentCardResolver.normalise({"name": "agent"})
    assert "url" in excinfo.value.missing


def test_empty_document_raises_discovery_error() -> None:
    """A fetcher returning nothing is reported as a discovery failure."""
    resolver = resolver_for({})
    with pytest.raises(DiscoveryError) as excinfo:
        resolver.discover("https://agent.example")
    assert excinfo.value.reason == "empty response"


def test_agent_card_requires_fields() -> None:
    """AgentCard rejects blank names and urls on construction."""
    with pytest.raises(CardValidationError):
        AgentCard(name="", version="1.0", url="https://a.example")
    with pytest.raises(CardValidationError):
        AgentCard(name="a", version="1.0", url="")


def test_supports_helper() -> None:
    """supports() reflects the declared capabilities."""
    card = AgentCard(name="a", version="1.0", url="https://a.example",
                     capabilities=("streaming",))
    assert card.supports("streaming") is True
    assert card.supports("push") is False


def test_as_dict_is_serialisable() -> None:
    """as_dict() exposes plain containers."""
    card = AgentCard(name="a", version="1.0", url="https://a.example",
                     capabilities=("x",), skills=("y",), metadata={"k": "v"})
    data = card.as_dict()
    assert data["capabilities"] == ["x"]
    assert data["metadata"] == {"k": "v"}


def test_metadata_is_flattened_to_strings() -> None:
    """Scalar metadata values are stringified, non-scalars dropped."""
    card = AgentCardResolver.normalise({
        "name": "agent",
        "url": "https://agent.example",
        "metadata": {"a": 1, "b": True, "c": [1, 2]},
    })
    assert card.metadata == {"a": "1", "b": "True"}


def test_invalid_capabilities_are_dropped() -> None:
    """Non-string capability entries are ignored."""
    card = AgentCardResolver.normalise({
        "name": "agent",
        "url": "https://agent.example",
        "capabilities": ["ok", 5, None, "  "],
    })
    assert card.capabilities == ("ok",)


def test_discover_many_skips_failures() -> None:
    """Batch discovery keeps healthy origins and skips broken ones."""
    good = "https://good.example" + WELL_KNOWN_PATH
    resolver = resolver_for({
        good: {"name": "good", "url": "https://good.example"},
    })
    cards = resolver.discover_many(["https://good.example", "https://bad.example"])
    assert list(cards) == ["https://good.example"]


def test_custom_well_known_path() -> None:
    """A custom well-known path is honoured."""
    resolver = AgentCardResolver(lambda url: None, well_known_path="/card.json")
    assert resolver.well_known_url("https://a.example") == "https://a.example/card.json"
