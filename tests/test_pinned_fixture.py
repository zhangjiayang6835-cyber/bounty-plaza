"""
Tests validating the pinned a2a-agent-card.json fixture against
the immutable acceptance criteria from benchmarks/direct-growth-v2/a2a-agent-card/check.py.
"""

import json
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent_card_discovery.models import AgentCard

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "a2a-agent-card.json"


def test_pinned_fixture_immutable_acceptance():
    assert FIXTURE_PATH.is_file(), f"missing required fixture: {FIXTURE_PATH}"
    content = FIXTURE_PATH.read_text(encoding="utf-8")
    fixture = json.loads(content)

    # 1. Product name
    assert (
        fixture.get("name") == "Agent Bounties"
    ), "Agent Card must use the canonical product name"

    # 2. Description and Version
    assert str(
        fixture.get("description", "")
    ).strip(), "Agent Card description is required"
    assert str(fixture.get("version", "")).strip(), "Agent Card version is required"

    # 3. Capabilities
    assert isinstance(
        fixture.get("capabilities"), dict
    ), "Agent Card capabilities are required"

    # 4. Default Input/Output Modes
    for field in ("defaultInputModes", "defaultOutputModes"):
        value = fixture.get(field)
        assert (
            isinstance(value, list) and value
        ), f"Agent Card {field} must be a non-empty array"

    # 5. Supported Interfaces
    interfaces = fixture.get("supportedInterfaces")
    assert (
        isinstance(interfaces, list) and interfaces
    ), "Agent Card must declare at least one interface"
    assert all(
        str(item.get("url", "")).startswith("https://api.agentbounties.app/")
        for item in interfaces
    ), "Agent Card interfaces must use the canonical HTTPS API"
    assert all(
        item.get("protocolVersion") == "1.0" for item in interfaces
    ), "every Agent Card interface must declare A2A 1.0"
    binding = "https://agentbounties.app/docs/a2a-direct-api-binding-v1"
    assert all(
        item.get("protocolBinding") == binding for item in interfaces
    ), "interfaces must identify the documented Agent Bounties custom binding"
    assert (
        "protocolVersion" not in fixture
    ), "protocolVersion belongs on interfaces, not the Agent Card root"

    # 6. Skills
    skills = fixture.get("skills")
    assert isinstance(skills, list), "Agent Card skills must be an array"
    for skill in skills:
        for field in ("id", "name", "description", "tags"):
            value = skill.get(field)
            assert (
                value is not None and value != "" and value != []
            ), f"Agent Card skill is missing {field}"

    skill_ids = {str(item.get("id", "")) for item in skills}
    required_skills = {
        "discover-funded-work",
        "plan-bounty-claim",
        "submit-bounty-evidence",
        "check-bounty-settlement",
        "post-bounty",
    }
    missing = required_skills - skill_ids
    assert not missing, f"Agent Card is missing skills: {sorted(missing)}"

    # 7. Forbidden material and required phrases
    serialized = json.dumps(fixture, sort_keys=True).lower()
    for forbidden in ("private_key", "private key", "seed phrase", "api_key", "secret"):
        assert (
            forbidden not in serialized
        ), f"Agent Card exposes forbidden material: {forbidden}"

    for required_phrase in ("canonical", "claimable", "bountysettled"):
        assert (
            required_phrase in serialized
        ), f"Agent Card must preserve the {required_phrase} evidence boundary"


def test_pinned_fixture_model_parsing():
    content = FIXTURE_PATH.read_text(encoding="utf-8")
    data = json.loads(content)
    card = AgentCard.from_dict(data)

    assert card.name == "Agent Bounties"
    assert card.version == "1.0.0"
    assert len(card.skills) == 5
    assert len(card.supported_interfaces) == 1
    assert card.supported_interfaces[0].protocol_version == "1.0"
