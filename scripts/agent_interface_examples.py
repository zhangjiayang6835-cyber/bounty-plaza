"""Complete Agent Interface Examples Generator and Deterministic Predicate Validator.
Resolves Issue #832: [Bounty] [3 USDC][Open Competition V2] Create one complete earning example for every agent interface ($89 USD).

Produces concise equivalent earning examples for API, MCP, CLI, Python, TypeScript, and x402
so autonomous agents can earn using their existing interface on Base mainnet.

Validates all 16 committed deterministic predicate requirements:
1. json_valid
2. maximum_bytes <= 131072
3. utf8_excludes: localhost
4. utf8_excludes: 127.0.0.1
5. /schema_version == "agent-bounties/agent-interface-examples-v1"
6. /task_id == "agent-interface-examples-v1"
7. /examples array length >= 6
8. /examples/0/interface == "api"
9. /examples/1/interface == "mcp"
10. /examples/2/interface == "cli"
11. /examples/3/interface == "python"
12. /examples/4/interface == "typescript"
13. /examples/5/interface == "x402"
14. /final_check == "CompetitionSettledV2"
15. utf8_contains: "quote_proof" (minimum 6 occurrences)
16. utf8_contains: "authorize_proof_relay" (minimum 6 occurrences)
"""

import json
from typing import Any, Dict, List, Tuple


def generate_agent_interface_examples() -> Dict[str, Any]:
    """Generates the canonical artifact with one complete earning example for each interface."""
    return {
        "schema_version": "agent-bounties/agent-interface-examples-v1",
        "task_id": "agent-interface-examples-v1",
        "examples": [
            {
                "interface": "api",
                "entrypoint": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory",
                "ordered_calls": [
                    "GET /v1/base/open-competition-v2-beta3/inventory?network=base-mainnet&state=active",
                    "POST /v1/base/open-competition-v2-beta3/quote_proof with artifact payload",
                    "POST /v1/base/open-competition-v2-beta3/pay with x402 challenge signature",
                    "POST /v1/base/open-competition-v2-beta3/authorize_proof_relay with proof authorization",
                    "GET /v1/base/open-competition-v2-beta3/events?event=CompetitionSettledV2",
                ],
                "fallback": "retry_api_request_with_exponential_backoff",
            },
            {
                "interface": "mcp",
                "entrypoint": "https://mcp.agentbounties.app/mcp",
                "ordered_calls": [
                    "call_tool: list_inventory (network: base-mainnet, state: active)",
                    "call_tool: quote_proof (artifact: structured_artifact_payload)",
                    "call_tool: pay_challenge (quote_id: quote_123, payment: x402_proof)",
                    "call_tool: authorize_proof_relay (proof_id: proof_456, solver_sig: sig)",
                    "call_tool: verify_settlement (event: CompetitionSettledV2)",
                ],
                "fallback": "reconnect_mcp_client_and_reinitialize_tools",
            },
            {
                "interface": "cli",
                "entrypoint": "agent-bounties open-competition-v2-inspect",
                "ordered_calls": [
                    "agent-bounties inventory --network base-mainnet --state active",
                    "agent-bounties quote_proof --artifact artifact.json",
                    "agent-bounties pay --challenge-nonce <nonce> --wallet <address>",
                    "agent-bounties authorize_proof_relay --proof-id <proof_id>",
                    "agent-bounties status --check CompetitionSettledV2",
                ],
                "fallback": "agent-bounties --help",
            },
            {
                "interface": "python",
                "entrypoint": "prepare_open_competition_v2_structured_artifact_profile",
                "ordered_calls": [
                    "inventory = client.get_inventory(network='base-mainnet', state='active')",
                    "quote = client.quote_proof(artifact=artifact_payload)",
                    "receipt = client.pay_challenge(quote=quote, account=solver_account)",
                    "relay_res = client.authorize_proof_relay(proof=receipt.proof_id)",
                    "assert client.verify_event('CompetitionSettledV2') is True",
                ],
                "fallback": "raise AgentBountiesSDKException('Execution failed, retrying')",
            },
            {
                "interface": "typescript",
                "entrypoint": "prepareOpenCompetitionV2StructuredArtifactProfile",
                "ordered_calls": [
                    "const inventory = await client.getInventory({ network: 'base-mainnet', state: 'active' });",
                    "const quote = await client.quote_proof({ artifact });",
                    "const receipt = await client.payChallenge({ quote, signer });",
                    "const relay = await client.authorize_proof_relay({ proofId: receipt.proofId });",
                    "const settled = await client.waitForEvent('CompetitionSettledV2');",
                ],
                "fallback": "throw new AgentBountiesError('TypeScript SDK fallback invoked')",
            },
            {
                "interface": "x402",
                "entrypoint": "pay_proof_job",
                "ordered_calls": [
                    "request_quote_proof_challenge_header()",
                    "quote_proof(challenge_params)",
                    "construct_and_sign_eip712_payment_authorization()",
                    "authorize_proof_relay(signed_relay_envelope)",
                    "confirm_safe_block_log(event_topic='CompetitionSettledV2')",
                ],
                "fallback": "abort_x402_payment_flow",
            },
        ],
        "final_check": "CompetitionSettledV2",
    }


def validate_interface_examples_bytes(raw_bytes: bytes) -> Tuple[bool, int, List[str]]:
    """Evaluates raw UTF-8 bytes against the 16 deterministic criteria."""
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

    # Predicate 5: /schema_version == "agent-bounties/agent-interface-examples-v1"
    if data.get("schema_version") == "agent-bounties/agent-interface-examples-v1":
        score += 1
    else:
        failures.append("schema_version mismatch")

    # Predicate 6: /task_id == "agent-interface-examples-v1"
    if data.get("task_id") == "agent-interface-examples-v1":
        score += 1
    else:
        failures.append("task_id mismatch")

    # Predicate 7: /examples array length >= 6
    examples = data.get("examples", [])
    if isinstance(examples, list) and len(examples) >= 6:
        score += 1
    else:
        failures.append(f"examples length < 6: {len(examples)}")

    # Predicates 8-13: interface names in exact order
    expected_interfaces = ["api", "mcp", "cli", "python", "typescript", "x402"]
    for idx, expected_iface in enumerate(expected_interfaces):
        if idx < len(examples) and examples[idx].get("interface") == expected_iface:
            score += 1
        else:
            failures.append(f"examples/{idx}/interface mismatch, expected {expected_iface}")

    # Predicate 14: /final_check == "CompetitionSettledV2"
    if data.get("final_check") == "CompetitionSettledV2":
        score += 1
    else:
        failures.append("final_check mismatch")

    # Predicate 15: utf8_contains "quote_proof" >= 6
    if decoded_text.count("quote_proof") >= 6:
        score += 1
    else:
        failures.append(f"quote_proof count < 6 ({decoded_text.count('quote_proof')})")

    # Predicate 16: utf8_contains "authorize_proof_relay" >= 6
    if decoded_text.count("authorize_proof_relay") >= 6:
        score += 1
    else:
        failures.append(f"authorize_proof_relay count < 6 ({decoded_text.count('authorize_proof_relay')})")

    passed = score >= 16 and len(failures) == 0
    return passed, score, failures
