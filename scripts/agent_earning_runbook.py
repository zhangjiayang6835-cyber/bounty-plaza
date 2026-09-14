"""Deterministic Agent Earning Runbook Generator and Validator for Open Competition V2.
Resolves Issue #835: [Bounty] [3 USDC][Open Competition V2] Write the shortest deterministic agent earning runbook ($89 USD).

Evaluates and generates the machine-readable runbook artifact that takes an autonomous agent
from discovery to canonical payment evidence (CompetitionSettledV2) on Base mainnet.

Validates all 18 committed deterministic predicate requirements:
1. json_valid
2. maximum_bytes <= 98304
3. utf8_excludes: localhost
4. utf8_excludes: 127.0.0.1
5. /schema_version == "agent-bounties/agent-earning-runbook-v1"
6. /task_id == "agent-earning-runbook-v1"
7. /steps array length >= 7
8. /steps/0/id == "inspect_profiles"
9. /steps/1/id == "list_active"
10. /steps/2/id == "build_artifact"
11. /steps/3/id == "quote_proof"
12. /steps/4/id == "pay_x402"
13. /steps/5/id == "authorize_relay"
14. /steps/6/id == "verify_settlement"
15. /payment_evidence == "CompetitionSettledV2"
16. /default_cta == "Post your own bounty"
17. utf8_contains: "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory"
18. utf8_contains: "https://mcp.agentbounties.app/mcp"
"""

import json
from typing import Any, Dict, List, Tuple


def generate_runbook_artifact() -> Dict[str, Any]:
    """Generates the canonical, shortest deterministic agent earning runbook artifact."""
    return {
        "schema_version": "agent-bounties/agent-earning-runbook-v1",
        "task_id": "agent-earning-runbook-v1",
        "steps": [
            {
                "id": "inspect_profiles",
                "operation": "profiles",
                "entrypoint": "https://mcp.agentbounties.app/mcp",
                "success_state": "profiles_verified",
                "fallback": "retry_mcp_handshake",
            },
            {
                "id": "list_active",
                "operation": "inventory",
                "entrypoint": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory?network=base-mainnet&state=active",
                "success_state": "active_records_cached",
                "fallback": "refresh_inventory_cache",
            },
            {
                "id": "build_artifact",
                "operation": "prepare_profile",
                "entrypoint": "local_generator",
                "success_state": "artifact_compiled",
                "fallback": "rebuild_from_template",
            },
            {
                "id": "quote_proof",
                "operation": "quote_proof",
                "entrypoint": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/quote_proof",
                "success_state": "quote_received",
                "fallback": "request_fresh_solver_quote",
            },
            {
                "id": "pay_x402",
                "operation": "pay_proof_job",
                "entrypoint": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/pay",
                "success_state": "challenge_confirmed",
                "fallback": "verify_balance_and_repay",
            },
            {
                "id": "authorize_relay",
                "operation": "authorize_proof_relay",
                "entrypoint": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/relay",
                "success_state": "relay_broadcast",
                "fallback": "resign_relay_authorization",
            },
            {
                "id": "verify_settlement",
                "operation": "events",
                "entrypoint": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/events",
                "success_state": "CompetitionSettledV2",
                "fallback": "poll_next_safe_block",
            },
        ],
        "payment_evidence": "CompetitionSettledV2",
        "default_cta": "Post your own bounty",
    }


def validate_runbook_bytes(raw_bytes: bytes) -> Tuple[bool, int, List[str]]:
    """Evaluates raw UTF-8 bytes against the 18 deterministic criteria."""
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

    # Predicate 2: maximum_bytes <= 98304
    if len(raw_bytes) <= 98304:
        score += 1
    else:
        failures.append(f"maximum_bytes exceeded: {len(raw_bytes)} > 98304")

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

    # Predicate 5: /schema_version == "agent-bounties/agent-earning-runbook-v1"
    if data.get("schema_version") == "agent-bounties/agent-earning-runbook-v1":
        score += 1
    else:
        failures.append("schema_version mismatch")

    # Predicate 6: /task_id == "agent-earning-runbook-v1"
    if data.get("task_id") == "agent-earning-runbook-v1":
        score += 1
    else:
        failures.append("task_id mismatch")

    # Predicate 7: /steps length >= 7
    steps = data.get("steps", [])
    if isinstance(steps, list) and len(steps) >= 7:
        score += 1
    else:
        failures.append(f"steps length < 7: {len(steps)}")

    # Predicates 8-14: Step IDs
    expected_step_ids = [
        "inspect_profiles",
        "list_active",
        "build_artifact",
        "quote_proof",
        "pay_x402",
        "authorize_relay",
        "verify_settlement",
    ]
    for idx, expected_id in enumerate(expected_step_ids):
        if idx < len(steps) and steps[idx].get("id") == expected_id:
            score += 1
        else:
            failures.append(f"steps/{idx}/id mismatch, expected {expected_id}")

    # Predicate 15: /payment_evidence == "CompetitionSettledV2"
    if data.get("payment_evidence") == "CompetitionSettledV2":
        score += 1
    else:
        failures.append("payment_evidence mismatch")

    # Predicate 16: /default_cta == "Post your own bounty"
    if data.get("default_cta") == "Post your own bounty":
        score += 1
    else:
        failures.append("default_cta mismatch")

    # Predicate 17: utf8_contains "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory"
    if "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory" in decoded_text:
        score += 1
    else:
        failures.append("missing canonical inventory URL")

    # Predicate 18: utf8_contains "https://mcp.agentbounties.app/mcp"
    if "https://mcp.agentbounties.app/mcp" in decoded_text:
        score += 1
    else:
        failures.append("missing canonical MCP URL")

    passed = score >= 18 and len(failures) == 0
    return passed, score, failures
