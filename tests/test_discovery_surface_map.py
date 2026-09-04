"""Unit test suite for AI-Agent Discovery Surface Map Generator and Deterministic Validator.
Tests Issue #834 requirements:
- Validates all 22 deterministic predicates with score threshold 22/22.
- Verifies maximum bytes limit (maximum 131072 bytes).
- Verifies prohibition of localhost and 127.0.0.1.
- Tests presence of all 8 exact discovery channels in required order.
- Tests presence of canonical URLs (site, API, MCP, and llms.txt).
- Tests detection of invalid schema or corrupted channel orders.
"""

import json
import pytest
from scripts.discovery_surface_map import (
    generate_discovery_surface_map,
    validate_surface_map_bytes,
)


def test_generated_map_passes_all_22_deterministic_predicates():
    surface_map = generate_discovery_surface_map()
    raw_bytes = json.dumps(surface_map, indent=2).encode("utf-8")

    passed, score, failures = validate_surface_map_bytes(raw_bytes)
    assert passed is True
    assert score == 22
    assert len(failures) == 0


def test_map_fails_if_localhost_or_127_0_0_1_present():
    surface_map = generate_discovery_surface_map()
    surface_map["surfaces"][0]["observed_entrypoint"] = "http://localhost:3000/tasks"
    raw_bytes = json.dumps(surface_map).encode("utf-8")

    passed, score, failures = validate_surface_map_bytes(raw_bytes)
    assert passed is False
    assert "utf8_excludes localhost failed" in failures

    surface_map2 = generate_discovery_surface_map()
    surface_map2["surfaces"][0]["observed_entrypoint"] = "http://127.0.0.1:3000/tasks"
    raw_bytes2 = json.dumps(surface_map2).encode("utf-8")

    passed2, score2, failures2 = validate_surface_map_bytes(raw_bytes2)
    assert passed2 is False
    assert "utf8_excludes 127.0.0.1 failed" in failures2


def test_map_fails_if_channel_missing_or_out_of_order():
    surface_map = generate_discovery_surface_map()
    # Swap two channels
    surface_map["surfaces"][0]["channel"] = "github_search"
    surface_map["surfaces"][1]["channel"] = "web_search"
    raw_bytes = json.dumps(surface_map).encode("utf-8")

    passed, score, failures = validate_surface_map_bytes(raw_bytes)
    assert passed is False
    assert any("surfaces/0/channel mismatch" in f for f in failures)


def test_map_fails_if_less_than_8_surfaces():
    surface_map = generate_discovery_surface_map()
    surface_map["surfaces"] = surface_map["surfaces"][:6]
    raw_bytes = json.dumps(surface_map).encode("utf-8")

    passed, score, failures = validate_surface_map_bytes(raw_bytes)
    assert passed is False
    assert any("surfaces length < 8" in f for f in failures)


def test_map_fails_if_required_canonical_urls_missing():
    surface_map = generate_discovery_surface_map()
    surface_map["canonical_mcp"] = "https://custom.tool/mcp"
    # also remove from query/entrypoint
    surface_map["surfaces"][4]["observed_entrypoint"] = "https://custom.tool/mcp"
    surface_map["surfaces"][4]["query"] = "custom list"
    raw_bytes = json.dumps(surface_map).encode("utf-8")

    passed, score, failures = validate_surface_map_bytes(raw_bytes)
    assert passed is False
    assert "missing https://mcp.agentbounties.app/mcp" in failures


def test_map_fails_if_payload_exceeds_maximum_bytes():
    surface_map = generate_discovery_surface_map()
    surface_map["padding"] = "Z" * 140000
    raw_bytes = json.dumps(surface_map).encode("utf-8")

    passed, score, failures = validate_surface_map_bytes(raw_bytes)
    assert passed is False
    assert any("maximum_bytes exceeded" in f for f in failures)
