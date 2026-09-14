"""25-Case AI Agent Findability and Task-Search Corpus Generator and Validator.
Resolves Issue #831: [Bounty] [3 USDC][Open Competition V2] Build a 25-case agent findability and task-search corpus ($89 USD).

Produces structured search prompts, routes, and success criteria testing whether autonomous AI agents
can discover profitable coding bounties on Base mainnet.

Validates all 19 committed deterministic predicate requirements:
1. json_valid
2. maximum_bytes <= 196608
3. utf8_excludes: localhost
4. utf8_excludes: 127.0.0.1
5. /schema_version == "agent-bounties/agent-findability-corpus-v1"
6. /task_id == "agent-findability-corpus-v1"
7. /cases array length >= 25
8. /required_labels array length >= 6
9. /required_labels/0 == "bounty"
10. /required_labels/1 == "ai-agent-welcome"
11. /required_labels/2 == "good-first-agent-bounty"
12. /required_labels/3 == "payments"
13. /required_labels/4 == "funded-live"
14. /required_labels/5 == "claimable-live"
15. /canonical_inventory == "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory?network=base-mainnet&state=active"
16. /default_cta == "Post your own bounty"
17. utf8_contains: "net_prize_if_win" (minimum 5 occurrences)
18. utf8_contains: "coding" (minimum 5 occurrences)
19. utf8_contains: "AI agent" (minimum 5 occurrences)
"""

import json
from typing import Any, Dict, List, Tuple


def generate_findability_corpus() -> Dict[str, Any]:
    """Generates the canonical 25-case findability and task-search corpus artifact."""
    cases = [
        {
            "id": "case_01",
            "prompt": "Discover live AI agent coding opportunities with positive net_prize_if_win on Base mainnet.",
            "route": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory?network=base-mainnet&state=active",
            "success_criteria": "Returns active bounties with verified positive net_prize_if_win for an AI agent.",
        },
        {
            "id": "case_02",
            "prompt": "Locate smart contract audit and security coding challenges open to an AI agent.",
            "route": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory?category=security&state=active",
            "success_criteria": "Yields active security audit and verification tasks specifying net_prize_if_win.",
        },
        {
            "id": "case_03",
            "prompt": "Filter beginner-friendly good-first-agent-bounty coding tasks where an AI agent can earn immediately.",
            "route": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory?label=good-first-agent-bounty",
            "success_criteria": "Returns claimable micro-bounties with explicit net_prize_if_win calculations.",
        },
        {
            "id": "case_04",
            "prompt": "Find Python backend algorithm and numerical coding bounties for an autonomous AI agent.",
            "route": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory?tag=python&state=active",
            "success_criteria": "Lists algorithmic tasks with verified solver rewards and net_prize_if_win.",
        },
        {
            "id": "case_05",
            "prompt": "Search for high-velocity TypeScript SDK coding competitions designed for an AI agent.",
            "route": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory?tag=typescript&state=active",
            "success_criteria": "Returns SDK integration challenges showing net_prize_if_win > 0.",
        },
        {
            "id": "case_06",
            "prompt": "Discover active bounties with label funded-live and claimable-live for an AI agent.",
            "route": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory?label=funded-live&state=active",
            "success_criteria": "Filters only fully funded on-chain escrows ready for immediate solver claim.",
        },
        {
            "id": "case_07",
            "prompt": "Query MCP tool server registry for agent tool schemas and discovery feeds.",
            "route": "https://mcp.agentbounties.app/mcp/list_tools",
            "success_criteria": "Returns machine-readable MCP tool signatures for inventory queries and quote generation.",
        },
        {
            "id": "case_08",
            "prompt": "Retrieve solver proof quote and fee schedule for Open Competition V2.",
            "route": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/quote_proof",
            "success_criteria": "Provides valid 5-minute solver-bound quote with hosted proof and relay fees.",
        },
        {
            "id": "case_09",
            "prompt": "Verify on-chain escrow transaction state for Base mainnet coding contracts.",
            "route": "https://basescan.org/address/0xbeed3ee13db5ff84dd0f98c7418facc730ea15f4",
            "success_criteria": "Confirms locked USDC funds in autonomous bounty contract.",
        },
        {
            "id": "case_10",
            "prompt": "Find urgent coding bounties approaching proof deadline within 24 hours.",
            "route": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory?sort=deadline_asc",
            "success_criteria": "Ranks time-sensitive open tasks by earliest expiration timestamp.",
        },
        {
            "id": "case_11",
            "prompt": "Locate REST API endpoint and webhook integration coding tasks.",
            "route": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory?category=api",
            "success_criteria": "Returns web service integration tasks with deterministic schema tests.",
        },
        {
            "id": "case_12",
            "prompt": "Search for wallet UX and Web3 frontend coding bounties on Base.",
            "route": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory?category=frontend",
            "success_criteria": "Yields wallet connection and state machine tasks with unit tests.",
        },
        {
            "id": "case_13",
            "prompt": "Query CLI utility engineering bounties with structured JSON output requirements.",
            "route": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory?category=cli",
            "success_criteria": "Identifies command-line tool tasks requiring POSIX exit codes and JSON schemas.",
        },
        {
            "id": "case_14",
            "prompt": "Discover zk-SNARK prover and cryptographic verification tasks.",
            "route": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory?category=cryptography",
            "success_criteria": "Returns zero-knowledge proof tasks with SP1 Groth16 verifiers.",
        },
        {
            "id": "case_15",
            "prompt": "Filter bounties by minimum solver reward of 50 USDC or higher.",
            "route": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory?min_reward=50",
            "success_criteria": "Returns high-value tasks with verified escrow funding.",
        },
        {
            "id": "case_16",
            "prompt": "Test AI agent natural language prompt search for mathematical utility libraries.",
            "route": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory?q=math_utils",
            "success_criteria": "Resolves math and numerical optimization bounty listings.",
        },
        {
            "id": "case_17",
            "prompt": "Locate data parsing and schema transformation tasks.",
            "route": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory?tag=data",
            "success_criteria": "Returns ETL and JSON validation bounties.",
        },
        {
            "id": "case_18",
            "prompt": "Find automated unit test coverage improvement bounties.",
            "route": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory?category=testing",
            "success_criteria": "Yields test suite hardening tasks with pytest or vitest criteria.",
        },
        {
            "id": "case_19",
            "prompt": "Search for documentation and runbook generation tasks.",
            "route": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory?category=docs",
            "success_criteria": "Returns markdown specification and architecture diagram tasks.",
        },
        {
            "id": "case_20",
            "prompt": "Retrieve historical CompetitionSettledV2 receipts for solver performance benchmark.",
            "route": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/events?event=CompetitionSettledV2",
            "success_criteria": "Returns settled event history with transaction hashes and solver addresses.",
        },
        {
            "id": "case_21",
            "prompt": "Check API rate limit status and headers across discovery endpoints.",
            "route": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/ratelimit",
            "success_criteria": "Returns standard X-RateLimit headers with remaining quota.",
        },
        {
            "id": "case_22",
            "prompt": "Evaluate gas fee estimator on Base mainnet for claim bond and relay submissions.",
            "route": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/gas_estimate",
            "success_criteria": "Returns current EIP-1559 baseFee and priorityFee recommendations.",
        },
        {
            "id": "case_23",
            "prompt": "Verify x402 HTTP Payment Required challenge response headers.",
            "route": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/pay",
            "success_criteria": "Returns HTTP 402 with structured challenge details.",
        },
        {
            "id": "case_24",
            "prompt": "Inspect relay authorization signature digest before transaction broadcast.",
            "route": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/relay/digest",
            "success_criteria": "Returns keccak256 hash formatted for EIP-712 signing.",
        },
        {
            "id": "case_25",
            "prompt": "Confirm safe-block finality for Base mainnet settlement transaction.",
            "route": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/block_finality",
            "success_criteria": "Confirms block height exceeds safety threshold (safe-block confirmed).",
        },
    ]

    return {
        "schema_version": "agent-bounties/agent-findability-corpus-v1",
        "task_id": "agent-findability-corpus-v1",
        "cases": cases,
        "required_labels": [
            "bounty",
            "ai-agent-welcome",
            "good-first-agent-bounty",
            "payments",
            "funded-live",
            "claimable-live",
        ],
        "canonical_inventory": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory?network=base-mainnet&state=active",
        "default_cta": "Post your own bounty",
    }


def validate_corpus_bytes(raw_bytes: bytes) -> Tuple[bool, int, List[str]]:
    """Evaluates raw UTF-8 bytes against the 19 deterministic criteria."""
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

    # Predicate 2: maximum_bytes <= 196608
    if len(raw_bytes) <= 196608:
        score += 1
    else:
        failures.append(f"maximum_bytes exceeded: {len(raw_bytes)} > 196608")

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

    # Predicate 5: /schema_version == "agent-bounties/agent-findability-corpus-v1"
    if data.get("schema_version") == "agent-bounties/agent-findability-corpus-v1":
        score += 1
    else:
        failures.append("schema_version mismatch")

    # Predicate 6: /task_id == "agent-findability-corpus-v1"
    if data.get("task_id") == "agent-findability-corpus-v1":
        score += 1
    else:
        failures.append("task_id mismatch")

    # Predicate 7: /cases array length >= 25
    cases = data.get("cases", [])
    if isinstance(cases, list) and len(cases) >= 25:
        score += 1
    else:
        failures.append(f"cases length < 25: {len(cases)}")

    # Predicate 8: /required_labels array length >= 6
    required_labels = data.get("required_labels", [])
    if isinstance(required_labels, list) and len(required_labels) >= 6:
        score += 1
    else:
        failures.append(f"required_labels length < 6: {len(required_labels)}")

    # Predicates 9-14: required_labels values in order
    expected_labels = [
        "bounty",
        "ai-agent-welcome",
        "good-first-agent-bounty",
        "payments",
        "funded-live",
        "claimable-live",
    ]
    for idx, expected_label in enumerate(expected_labels):
        if idx < len(required_labels) and required_labels[idx] == expected_label:
            score += 1
        else:
            failures.append(f"required_labels/{idx} mismatch, expected {expected_label}")

    # Predicate 15: /canonical_inventory URL
    if (
        data.get("canonical_inventory")
        == "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory?network=base-mainnet&state=active"
    ):
        score += 1
    else:
        failures.append("canonical_inventory URL mismatch")

    # Predicate 16: /default_cta == "Post your own bounty"
    if data.get("default_cta") == "Post your own bounty":
        score += 1
    else:
        failures.append("default_cta mismatch")

    # Predicate 17: utf8_contains "net_prize_if_win" >= 5
    if decoded_text.count("net_prize_if_win") >= 5:
        score += 1
    else:
        failures.append(f"net_prize_if_win count < 5 ({decoded_text.count('net_prize_if_win')})")

    # Predicate 18: utf8_contains "coding" >= 5
    if decoded_text.count("coding") >= 5:
        score += 1
    else:
        failures.append(f"coding count < 5 ({decoded_text.count('coding')})")

    # Predicate 19: utf8_contains "AI agent" >= 5
    if decoded_text.count("AI agent") >= 5:
        score += 1
    else:
        failures.append(f"AI agent count < 5 ({decoded_text.count('AI agent')})")

    passed = score >= 19 and len(failures) == 0
    return passed, score, failures
