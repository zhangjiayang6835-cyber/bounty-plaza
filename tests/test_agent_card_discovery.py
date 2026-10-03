"""
Unit tests for agent card discovery, canonical URL normalization,
deterministic sorting, validation, and fault-tolerant batch discovery.
"""

import json
import sys
from pathlib import Path

import pytest

# Ensure src is in sys.path
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent_card_discovery.canonical_url import canonicalize_url
from agent_card_discovery.discovery import (
    discover_many,
)
from agent_card_discovery.errors import (
    InvalidFieldTypeError,
    InvalidUrlError,
    MissingFieldError,
    SecurityViolationError,
)
from agent_card_discovery.models import (
    AgentCard,
    AgentInterface,
    normalize_string_list,
)

# ── Canonical URL Tests ──────────────────────────────────────────────────


class TestCanonicalUrl:
    def test_strip_default_http_port_80(self):
        assert canonicalize_url("http://example.com:80/api") == "http://example.com/api"

    def test_strip_default_https_port_443(self):
        assert (
            canonicalize_url("https://example.com:443/api") == "https://example.com/api"
        )

    def test_preserve_custom_ports(self):
        assert (
            canonicalize_url("http://example.com:8080/api")
            == "http://example.com:8080/api"
        )
        assert (
            canonicalize_url("https://example.com:8443/api")
            == "https://example.com:8443/api"
        )

    def test_lowercase_scheme_and_hostname(self):
        assert (
            canonicalize_url("HTTPS://API.AGENTBOUNTIES.APP/a2a/v1")
            == "https://api.agentbounties.app/a2a/v1"
        )

    def test_remove_redundant_double_slashes(self):
        assert (
            canonicalize_url("https://example.com//a2a//v1//card.json")
            == "https://example.com/a2a/v1/card.json"
        )

    def test_keep_query_and_fragment(self):
        url = "https://example.com:443//api//v1?version=1.0&auth=jwt#section"
        assert (
            canonicalize_url(url)
            == "https://example.com/api/v1?version=1.0&auth=jwt#section"
        )

    def test_invalid_url_raises_typed_error(self):
        with pytest.raises(InvalidUrlError):
            canonicalize_url("")

        with pytest.raises(InvalidUrlError):
            canonicalize_url("   ")

        with pytest.raises(InvalidUrlError):
            canonicalize_url("not_a_url")

        with pytest.raises(InvalidUrlError):
            canonicalize_url(123)  # type: ignore


# ── Deterministic Normalization Tests ────────────────────────────────────


class TestDeterministicNormalization:
    def test_normalize_string_list_dedupes_and_sorts(self):
        raw = [" python ", "rust", "python", " go ", "  rust  "]
        assert normalize_string_list(raw, "tags") == ["go", "python", "rust"]

    def test_skills_sorted_by_id_and_tags_sorted(self):
        raw_card = {
            "name": "Test Agent",
            "description": "Agent description",
            "version": "1.0.0",
            "capabilities": {"streaming": False, "push": True},
            "defaultInputModes": ["application/json"],
            "defaultOutputModes": ["application/json"],
            "supportedInterfaces": [
                {
                    "url": "https://api.example.com/a2a/v1",
                    "protocolBinding": "HTTP+JSON",
                }
            ],
            "skills": [
                {
                    "id": "z-skill",
                    "name": "Z Skill",
                    "description": "Z skill description",
                    "tags": ["beta", "alpha"],
                },
                {
                    "id": "a-skill",
                    "name": "A Skill",
                    "description": "A skill description",
                    "tags": ["delta", "gamma"],
                },
            ],
        }
        card = AgentCard.from_dict(raw_card)
        assert [s.id for s in card.skills] == ["a-skill", "z-skill"]
        assert card.skills[0].tags == ["delta", "gamma"]
        assert card.skills[1].tags == ["alpha", "beta"]

    def test_spec_version_fallback_to_1_0(self):
        raw_interface = {
            "url": "https://api.example.com/a2a/v1",
            "protocolBinding": "HTTP+JSON",
            # protocolVersion intentionally omitted
        }
        iface = AgentInterface.from_dict(raw_interface)
        assert iface.protocol_version == "1.0"


# ── Required Field Validation & Typed Errors ─────────────────────────────


class TestValidationAndErrors:
    @pytest.fixture
    def valid_card_data(self):
        return {
            "name": "Test Agent",
            "description": "Valid agent description",
            "version": "1.0.0",
            "capabilities": {"custom": True},
            "defaultInputModes": ["application/json"],
            "defaultOutputModes": ["application/json"],
            "supportedInterfaces": [
                {"url": "https://api.example.com/v1", "protocolBinding": "HTTP+JSON"}
            ],
            "skills": [
                {
                    "id": "task-solve",
                    "name": "Task Solver",
                    "description": "Solves tasks",
                    "tags": ["solver"],
                }
            ],
        }

    def test_missing_name_raises_missing_field_error(self, valid_card_data):
        del valid_card_data["name"]
        with pytest.raises(MissingFieldError) as exc:
            AgentCard.from_dict(valid_card_data)
        assert exc.value.field_name == "name"

    def test_missing_description_raises_missing_field_error(self, valid_card_data):
        valid_card_data["description"] = ""
        with pytest.raises(MissingFieldError) as exc:
            AgentCard.from_dict(valid_card_data)
        assert exc.value.field_name == "description"

    def test_missing_capabilities_raises_missing_field_error(self, valid_card_data):
        del valid_card_data["capabilities"]
        with pytest.raises(MissingFieldError) as exc:
            AgentCard.from_dict(valid_card_data)
        assert exc.value.field_name == "capabilities"

    def test_missing_interfaces_raises_missing_field_error(self, valid_card_data):
        valid_card_data["supportedInterfaces"] = []
        with pytest.raises(MissingFieldError) as exc:
            AgentCard.from_dict(valid_card_data)
        assert "supportedInterfaces" in exc.value.field_name

    def test_missing_skills_raises_missing_field_error(self, valid_card_data):
        valid_card_data["skills"] = []
        with pytest.raises(MissingFieldError) as exc:
            AgentCard.from_dict(valid_card_data)
        assert "skills" in exc.value.field_name

    def test_forbidden_material_raises_security_violation_error(self, valid_card_data):
        valid_card_data["secret"] = "my-super-secret-key"
        with pytest.raises(SecurityViolationError):
            AgentCard.from_dict(valid_card_data)

    def test_invalid_type_raises_invalid_field_type_error(self, valid_card_data):
        valid_card_data["capabilities"] = 12345
        with pytest.raises(InvalidFieldTypeError):
            AgentCard.from_dict(valid_card_data)


# ── Fault-Tolerant discover_many Tests ───────────────────────────────────


class TestDiscoverMany:
    def test_discover_many_fault_tolerant(self):
        valid_payload = json.dumps(
            {
                "name": "Agent A",
                "description": "Agent A description",
                "version": "1.0.0",
                "capabilities": {},
                "defaultInputModes": ["application/json"],
                "defaultOutputModes": ["application/json"],
                "supportedInterfaces": [
                    {"url": "https://a.com/a2a", "protocolBinding": "HTTP+JSON"}
                ],
                "skills": [
                    {
                        "id": "skill-a",
                        "name": "Skill A",
                        "description": "Does A",
                        "tags": ["a"],
                    }
                ],
            }
        ).encode("utf-8")

        def mock_opener(req, timeout):
            if "fail.com" in req.full_url:
                raise ConnectionError("Network connection refused")
            if "invalid.com" in req.full_url:
                return b'{"invalid": "payload missing required fields"}'
            return valid_payload

        urls = [
            "https://valid1.com/card.json",
            "https://fail.com/card.json",
            "https://valid2.com/card.json",
            "https://invalid.com/card.json",
        ]

        # 1. Default mode: returns successful cards only without raising
        cards = discover_many(urls, opener=mock_opener)
        assert len(cards) == 2
        assert all(isinstance(c, AgentCard) for c in cards)

        # 2. Return exceptions mode: returns tuple (successes, failures)
        successes, failures = discover_many(
            urls, return_exceptions=True, opener=mock_opener
        )
        assert len(successes) == 2
        assert len(failures) == 2
        failed_urls = [f[0] for f in failures]
        assert "https://fail.com/card.json" in failed_urls
        assert "https://invalid.com/card.json" in failed_urls
