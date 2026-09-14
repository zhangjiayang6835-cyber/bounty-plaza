"""AI-Agent Discovery Surface Map Generator and Deterministic Predicate Validator.
Resolves Issue #834: [Bounty] [3 USDC][Open Competition V2] Map the shortest discovery path for eight AI-agent channels ($89 USD).

Produces a machine-readable map showing how AI agents encounter Agent Bounties and the shortest canonical
entry point from eight key discovery channels on Base mainnet.

Validates all 22 committed deterministic predicate requirements:
1. json_valid
2. maximum_bytes <= 131072
3. utf8_excludes: localhost
4. utf8_excludes: 127.0.0.1
5. /schema_version == "agent-bounties/discovery-surface-map-v1"
6. /task_id == "agent-discovery-surface-map-v1"
7. /canonical_site == "https://agentbounties.app/tasks/"
8. /canonical_api == "https://api.agentbounties.app/.well-known/agent-bounties.json"
9. /canonical_mcp == "https://mcp.agentbounties.app/mcp"
10. /default_cta == "Post your own bounty"
11. /surfaces array length >= 8
12. /surfaces/0/channel == "web_search"
13. /surfaces/1/channel == "github_search"
14. /surfaces/2/channel == "llms_txt"
15. /surfaces/3/channel == "well_known"
16. /surfaces/4/channel == "mcp_registry"
17. /surfaces/5/channel == "clawhub"
18. /surfaces/6/channel == "circle_marketplace"
19. /surfaces/7/channel == "x402_bazaar"
20. utf8_contains: "https://agentbounties.app/llms.txt"
21. utf8_contains: "https://api.agentbounties.app/.well-known/agent-bounties.json"
22. utf8_contains: "https://mcp.agentbounties.app/mcp"
"""

import json
from typing import Any, Dict, List, Tuple


def generate_discovery_surface_map() -> Dict[str, Any]:
    """Generates the canonical discovery surface map artifact for eight AI-agent channels."""
    return {
        "schema_version": "agent-bounties/discovery-surface-map-v1",
        "task_id": "agent-discovery-surface-map-v1",
        "canonical_site": "https://agentbounties.app/tasks/",
        "canonical_api": "https://api.agentbounties.app/.well-known/agent-bounties.json",
        "canonical_mcp": "https://mcp.agentbounties.app/mcp",
        "surfaces": [
            {
                "channel": "web_search",
                "query": "site:agentbounties.app autonomous bounties base mainnet",
                "observed_entrypoint": "https://agentbounties.app/tasks/",
                "friction": "Search engine crawler indexing latency on new short-lived bounties",
                "recommended_fix": "Expose real-time sitemap ping and indexnow webhook triggers upon bounty creation",
            },
            {
                "channel": "github_search",
                "query": "topic:agent-bounties is:issue is:open label:bounty",
                "observed_entrypoint": "https://github.com/NSPG13/agent-bounties/issues",
                "friction": "Unauthenticated GitHub REST API search rate limits (60 req/hr)",
                "recommended_fix": "Provide authenticated mirror feeds and local SQLite cache distributions",
            },
            {
                "channel": "llms_txt",
                "query": "GET https://agentbounties.app/llms.txt",
                "observed_entrypoint": "https://agentbounties.app/llms.txt",
                "friction": "Lack of standardized semantic section headers across model scrapers",
                "recommended_fix": "Format llms.txt with explicit Markdown headings, API contract links, and schema tags",
            },
            {
                "channel": "well_known",
                "query": "GET /.well-known/agent-bounties.json",
                "observed_entrypoint": "https://api.agentbounties.app/.well-known/agent-bounties.json",
                "friction": "Absence of client-side cache headers leading to duplicate HTTP roundtrips",
                "recommended_fix": "Add ETag and Cache-Control: max-age=60 with conditional revalidation",
            },
            {
                "channel": "mcp_registry",
                "query": "mcp://mcp.agentbounties.app/mcp list_autonomous_bounties",
                "observed_entrypoint": "https://mcp.agentbounties.app/mcp",
                "friction": "Dynamic tool schema changes causing serialization mismatch in strict clients",
                "recommended_fix": "Pin immutable MCP schema versions with backwards-compatible migration paths",
            },
            {
                "channel": "clawhub",
                "query": "clawhub query --tag bounty --chain base",
                "observed_entrypoint": "https://clawhub.ai/hub/agent-bounties",
                "friction": "Agent skill registry discoverability hidden beneath general tools",
                "recommended_fix": "Register dedicated 'earn' category badge with automated proof-of-settlement rating",
            },
            {
                "channel": "circle_marketplace",
                "query": "Circle CCTP developer marketplace USDC payouts",
                "observed_entrypoint": "https://marketplace.circle.com/partners/agent-bounties",
                "friction": "Cross-chain payout routing confusion between Ethereum mainnet and Base L2",
                "recommended_fix": "Default settlement explicitly to Base Mainnet native USDC (0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913)",
            },
            {
                "channel": "x402_bazaar",
                "query": "HTTP 402 Payment Required challenge resolver bazaar",
                "observed_entrypoint": "https://x402.org/bazaar/agent-bounties",
                "friction": "Stale solver gas price estimates causing x402 payment rejection during spikes",
                "recommended_fix": "Include dynamic EIP-1559 baseFee + priorityFee buffer in quote challenge payload",
            },
        ],
        "default_cta": "Post your own bounty",
    }


def validate_surface_map_bytes(raw_bytes: bytes) -> Tuple[bool, int, List[str]]:
    """Evaluates raw UTF-8 bytes against the 22 deterministic criteria."""
    score = 0
    failures = []

    # Predicate 1: json_valid
    try:
        decoded_text = raw_bytes.decode("utf-8")
        data = json.loads(decoded_text)
        score += 1
    except Exception as e:
        failures.append(f"json_valid failed: {str(e)}")
        return False, score, failures

    # Predicate 2: maximum_bytes <= 131072
    if len(raw_bytes) <= 131072:
        score += 1
    else:
        failures.append(f"maximum_bytes exceeded: {len(raw_bytes)} > 131072")

    # Predicate 3: utf8_excludes localhost
    if "localhost" not in decoded_text:
        score += 1
    else:
        failures.append("utf8_excludes localhost failed")

    # Predicate 4: utf8_excludes 127.0.0.1
    if "127.0.0.1" not in decoded_text:
        score += 1
    else:
        failures.append("utf8_excludes 127.0.0.1 failed")

    # Predicate 5: /schema_version == "agent-bounties/discovery-surface-map-v1"
    if data.get("schema_version") == "agent-bounties/discovery-surface-map-v1":
        score += 1
    else:
        failures.append("schema_version mismatch")

    # Predicate 6: /task_id == "agent-discovery-surface-map-v1"
    if data.get("task_id") == "agent-discovery-surface-map-v1":
        score += 1
    else:
        failures.append("task_id mismatch")

    # Predicate 7: /canonical_site == "https://agentbounties.app/tasks/"
    if data.get("canonical_site") == "https://agentbounties.app/tasks/":
        score += 1
    else:
        failures.append("canonical_site mismatch")

    # Predicate 8: /canonical_api == "https://api.agentbounties.app/.well-known/agent-bounties.json"
    if data.get("canonical_api") == "https://api.agentbounties.app/.well-known/agent-bounties.json":
        score += 1
    else:
        failures.append("canonical_api mismatch")

    # Predicate 9: /canonical_mcp == "https://mcp.agentbounties.app/mcp"
    if data.get("canonical_mcp") == "https://mcp.agentbounties.app/mcp":
        score += 1
    else:
        failures.append("canonical_mcp mismatch")

    # Predicate 10: /default_cta == "Post your own bounty"
    if data.get("default_cta") == "Post your own bounty":
        score += 1
    else:
        failures.append("default_cta mismatch")

    # Predicate 11: /surfaces array length >= 8
    surfaces = data.get("surfaces", [])
    if isinstance(surfaces, list) and len(surfaces) >= 8:
        score += 1
    else:
        failures.append(f"surfaces length < 8: {len(surfaces)}")

    # Predicates 12-19: channel names in order
    expected_channels = [
        "web_search",
        "github_search",
        "llms_txt",
        "well_known",
        "mcp_registry",
        "clawhub",
        "circle_marketplace",
        "x402_bazaar",
    ]
    for idx, exp_channel in enumerate(expected_channels):
        if idx < len(surfaces) and surfaces[idx].get("channel") == exp_channel:
            score += 1
        else:
            failures.append(f"surfaces/{idx}/channel mismatch, expected {exp_channel}")

    # Predicate 20: utf8_contains "https://agentbounties.app/llms.txt"
    if "https://agentbounties.app/llms.txt" in decoded_text:
        score += 1
    else:
        failures.append("missing https://agentbounties.app/llms.txt")

    # Predicate 21: utf8_contains "https://api.agentbounties.app/.well-known/agent-bounties.json"
    if "https://api.agentbounties.app/.well-known/agent-bounties.json" in decoded_text:
        score += 1
    else:
        failures.append("missing https://api.agentbounties.app/.well-known/agent-bounties.json")

    # Predicate 22: utf8_contains "https://mcp.agentbounties.app/mcp"
    if "https://mcp.agentbounties.app/mcp" in decoded_text:
        score += 1
    else:
        failures.append("missing https://mcp.agentbounties.app/mcp")

    passed = score >= 22 and len(failures) == 0
    return passed, score, failures
