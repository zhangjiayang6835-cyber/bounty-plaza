"""Command-line interface for Agent Bounties MCP child seeder."""

import argparse
import json
import sys
from typing import Optional
from packages.agent_bounties_mcp_seeder.models import (
    DeterministicMcpTaskVector,
    McpResponseTelemetry,
    McpToolDefinition,
    ParticipantRole,
    canonicalize_json_payload,
    compute_sha256_digest,
)
from packages.agent_bounties_mcp_seeder.seeder import McpBountySeeder


def create_cli_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser for agent bounties seeder.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        description="Autonomous Agent Bounties MCP Child Seeder and Settlement Engine"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed_parser = subparsers.add_parser("seed", help="Seed a new child MCP coding bounty")
    seed_parser.add_argument("--parent", required=True, help="Parent bounty contract address")
    seed_parser.add_argument("--title", required=True, help="Task title")
    seed_parser.add_argument("--description", required=True, help="Task description")
    seed_parser.add_argument("--reward", type=float, default=0.90, help="Solver reward in USDC")
    seed_parser.add_argument("--bond", type=float, default=0.10, help="Solver bond in USDC")

    margin_parser = subparsers.add_parser("margin", help="Calculate economic margins")
    margin_parser.add_argument("--parent-reward", type=float, default=2.00)
    margin_parser.add_argument("--child-funding", type=float, default=1.00)

    demo_parser = subparsers.add_parser("demo", help="Run deterministic end-to-end simulation")
    demo_parser.add_argument("--parent", default="0x43d42cb227d76588ab16693f14efd6cff851fa7a")

    verify_parser = subparsers.add_parser("verify", help="Run verification check")
    verify_parser.add_argument("--parent", default="0x43d42cb227d76588ab16693f14efd6cff851fa7a")

    return parser


def create_sample_mcp_vector() -> tuple[DeterministicMcpTaskVector, McpResponseTelemetry]:
    """Create sample deterministic MCP task vector and telemetry."""
    tool_def = McpToolDefinition(
        name="file_system_reader",
        description="Read file contents and return structured text.",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    )

    response_payload = {
        "text": "Canonical MCP tool content verified",
        "type": "text",
    }
    canonical_response = canonicalize_json_payload(response_payload)
    expected_digest = compute_sha256_digest(canonical_response)

    task_vector = DeterministicMcpTaskVector(
        tool_definition=tool_def,
        arguments={"path": "/workspace/target.txt"},
        expected_text="Canonical MCP tool content verified",
        expected_schema_keys=("text", "type"),
        expected_response_digest=expected_digest,
        max_latency_ms=250.0,
    )

    telemetry = McpResponseTelemetry(
        tool_name="file_system_reader",
        arguments={"path": "/workspace/target.txt"},
        response_content=canonical_response,
        response_digest=expected_digest,
        is_error=False,
        latency_ms=45.2,
    )

    return task_vector, telemetry


def run_demo(parent_address: str) -> dict[str, object]:
    """Execute end-to-end lifecycle demonstration and return verification payload.

    Args:
        parent_address: Parent bounty address.

    Returns:
        Dictionary containing verified simulation telemetry.
    """
    seeder = McpBountySeeder()

    creator = "0x52513a733d4b52282f2b4f5a91d965d38b64f3bb"
    solver = "0x62f7793b28dfa508067b186144a23c49dd0bf02f"

    seeder.register_participant(creator, ParticipantRole.PARENT_CREATOR, timestamp=100)
    seeder.register_participant(solver, ParticipantRole.CHILD_SOLVER, timestamp=110)

    spec = seeder.publish_child_terms(
        parent_bounty_id=parent_address,
        title="MCP: High-Performance Deterministic Tool Server",
        description="Implement Model Context Protocol server exposing tools/call capability.",
        reward_tuple=(0.90, 0.10),
        timestamp=120,
    )

    seeder.fund_child_escrow(spec.bounty_id, creator, amount_usdc=1.00, timestamp=130)
    seeder.claim_parent_bounty(
        parent_address, spec.bounty_id, creator, bond_usdc=0.01, timestamp=140
    )
    seeder.claim_child_bounty(spec.bounty_id, solver, bond_usdc=0.10, timestamp=150)

    task_vector, telemetry = create_sample_mcp_vector()

    receipt = seeder.record_mcp_execution(
        child_bounty_id=spec.bounty_id,
        solver_address=solver,
        telemetry=telemetry,
        timestamp=160,
    )

    settlement_receipt, proof_payload, margin = seeder.verify_and_settle(
        child_bounty_id=spec.bounty_id,
        receipt=receipt,
        task_vector=task_vector,
        timestamp=170,
    )

    result: dict[str, object] = {
        "status": "success",
        "child_bounty_id": spec.bounty_id,
        "parent_bounty_id": parent_address,
        "bounty_status": seeder.bounty_states[spec.bounty_id].value,
        "quorum_passed": True,
        "solver_payout_usdc": settlement_receipt.payout_usdc,
        "bond_refund_usdc": spec.bond_usdc,
        "parent_reward_usdc": margin.parent_reward_usdc,
        "gross_profit_usdc": margin.gross_profit_usdc,
        "net_margin_percentage": margin.net_margin_percentage,
        "settlement_transaction": settlement_receipt.transaction_hash,
        "encoded_abi_proof": proof_payload.encoded_abi,
        "payout_routing_evm": margin.payout_routing_evm,
        "payout_routing_stellar": margin.payout_routing_stellar,
    }
    return result


def main(argv: Optional[list[str]] = None) -> int:
    """Run CLI entrypoint.

    Args:
        argv: Command-line argument list, defaults to sys.argv[1:].

    Returns:
        Integer exit code.
    """
    parser = create_cli_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if args.command in ("demo", "verify"):
        demo_result = run_demo(args.parent)
        print(json.dumps(demo_result, indent=2))
        return 0

    if args.command == "margin":
        seeder = McpBountySeeder()
        margin = seeder.analyze_economic_margins(
            parent_reward=args.parent_reward,
            child_funding=args.child_funding,
        )
        print(json.dumps(margin.__dict__, indent=2))
        return 0

    if args.command == "seed":
        seeder = McpBountySeeder()
        spec = seeder.publish_child_terms(
            parent_bounty_id=args.parent,
            title=args.title,
            description=args.description,
            reward_tuple=(args.reward, args.bond),
        )
        print(
            json.dumps(
                {
                    "bounty_id": spec.bounty_id,
                    "parent_bounty_id": spec.parent_bounty_id,
                    "title": spec.title,
                    "reward_usdc": spec.solver_reward_usdc,
                    "bond_usdc": spec.bond_usdc,
                    "total_funding_usdc": spec.total_funding_usdc,
                },
                indent=2,
            )
        )
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
