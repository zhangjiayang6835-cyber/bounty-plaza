"""Command-line interface and demonstration runner for MCP child bounty seeder."""

import argparse
import json
import sys
from typing import Any, Sequence
from packages.mcp_child_bounty_seeder.models import (
    MCPCapabilityType,
    MCPMethodType,
    MCPToolSpec,
    MCPTaskVector,
    ParticipantRole,
    compute_sha256_digest,
)
from packages.mcp_child_bounty_seeder.seeder import (
    DEFAULT_PARENT_BOUNTY_ID,
    MCPChildBountySeeder,
)


def run_demo(parent_bounty_id: str = DEFAULT_PARENT_BOUNTY_ID) -> dict[str, Any]:
    """Execute end-to-end demonstration of child MCP bounty lifecycle.

    Args:
        parent_bounty_id: Parent bounty contract address on Base network.

    Returns:
        Structured dictionary recording state transitions and settlement proof.
    """
    seeder = MCPChildBountySeeder()

    creator_addr = "0x7b056457d04bcdbb5851112d007168aba30adf49"
    solver_addr = "0x95222290dd7278aa3ddd389cc1e1d165cc4bafe5"
    t0 = 1728000000

    seeder.register_participant(creator_addr, ParticipantRole.PARENT_CREATOR, t0)
    seeder.register_participant(solver_addr, ParticipantRole.CHILD_SOLVER, t0 + 10)

    payload = json.dumps(
        {
            "tool": "validate_agent_bounties_manifest",
            "protocol_version": "2024-11-05",
            "method": "tools/call",
            "status": "SUCCESS",
            "validation": {
                "base_earning_endpoints": True,
                "usdc_settlement": True,
                "mcp_tools_exposed": True,
            },
        },
        sort_keys=True,
    )

    tool_spec = MCPToolSpec(
        name="validate_agent_bounties_manifest",
        description="Validate canonical Base USDC earning endpoints and required MCP tools",
        target_method=MCPMethodType.TOOLS_CALL,
        required_capabilities=(MCPCapabilityType.TOOLS, MCPCapabilityType.RESOURCES),
    )

    task_vector = MCPTaskVector(
        tool=tool_spec,
        protocol_version="2024-11-05",
        test_suite="mcp_regression_v1",
        arguments=("--validate", "--canonical-base"),
        expected_exit_code=0,
        expected_digest=compute_sha256_digest(payload),
    )

    spec = seeder.publish_child_terms(
        parent_bounty_id=parent_bounty_id,
        title="Model Context Protocol Coding Task",
        description="Implement and verify canonical Base USDC earning discovery MCP tool",
        timestamp=t0 + 20,
    )

    seeder.fund_child_escrow(spec.bounty_id, creator_addr, 1.00, t0 + 30)
    seeder.claim_parent_bounty(parent_bounty_id, spec.bounty_id, creator_addr, 0.01, t0 + 40)
    seeder.claim_child_bounty(spec.bounty_id, solver_addr, 0.10, t0 + 50)

    receipt = seeder.record_execution(spec.bounty_id, solver_addr, payload, 0, t0 + 60)
    quorum, settlement, proof = seeder.settle_child_bounty(receipt, task_vector, t0 + 70)
    econ = seeder.calculate_economics()

    demo_data: dict[str, Any] = {
        "parent_bounty_id": parent_bounty_id,
        "child_bounty_id": spec.bounty_id,
        "creator_address": creator_addr,
        "solver_address": solver_addr,
        "total_child_funding_usdc": spec.total_funding_usdc,
        "solver_payout_usdc": settlement.payout_usdc,
        "quorum_passed": quorum.passed,
        "quorum_threshold": quorum.threshold,
        "transaction_hash": settlement.transaction_hash,
        "encoded_parent_proof": proof.encoded_abi,
        "gross_profit_usdc": econ.gross_profit_usdc,
        "net_margin_percentage": econ.net_margin_percentage,
        "payout_routing_evm": econ.payout_routing_evm,
        "payout_routing_stellar": econ.payout_routing_stellar,
    }
    return demo_data


def cli_main(args: Sequence[str] | None = None) -> int:
    """Main CLI entrypoint for child MCP bounty orchestration.

    Args:
        args: Command-line arguments.

    Returns:
        0 on success, non-zero on failure.
    """
    parser = argparse.ArgumentParser(
        description="Autonomous MCP Child Bounty Seeder CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed_parser = subparsers.add_parser("seed", help="Publish child bounty terms")
    seed_parser.add_argument(
        "--parent-bounty",
        default=DEFAULT_PARENT_BOUNTY_ID,
        help="Parent bounty address",
    )
    seed_parser.add_argument(
        "--title",
        default="Model Context Protocol Coding Task",
        help="Child bounty title",
    )

    margin_parser = subparsers.add_parser("margin", help="Calculate economic margins")
    margin_parser.add_argument(
        "--parent-reward",
        type=float,
        default=2.00,
        help="Parent reward USDC",
    )
    margin_parser.add_argument(
        "--child-funding",
        type=float,
        default=1.00,
        help="Child funding USDC",
    )

    subparsers.add_parser("demo", help="Run full end-to-end lifecycle demonstration")

    parsed = parser.parse_args(args)

    if parsed.command == "demo":
        demo_results = run_demo()
        print(json.dumps(demo_results, indent=2))
        return 0

    if parsed.command == "margin":
        seeder = MCPChildBountySeeder()
        analysis = seeder.calculate_economics(
            parent_reward_usdc=parsed.parent_reward,
            child_funding_usdc=parsed.child_funding,
        )
        print("Economic Margin Analysis:")
        print(f"  Parent Reward: {analysis.parent_reward_usdc:.2f} USDC")
        print(f"  Child Funding: {analysis.child_funding_usdc:.2f} USDC")
        print(f"  Gross Profit:  {analysis.gross_profit_usdc:.2f} USDC")
        print(f"  Margin:        {analysis.net_margin_percentage:.1f}%")
        print(f"  EVM Payout:    {analysis.payout_routing_evm}")
        print(f"  Stellar:       {analysis.payout_routing_stellar}")
        return 0

    if parsed.command == "seed":
        seeder = MCPChildBountySeeder()
        spec = seeder.publish_child_terms(
            parent_bounty_id=parsed.parent_bounty,
            title=parsed.title,
            description="Autonomous deterministic MCP child bounty",
        )
        seed_output = {
            "child_bounty_id": spec.bounty_id,
            "parent_bounty_id": spec.parent_bounty_id,
            "title": spec.title,
            "reward_usdc": spec.solver_reward_usdc,
            "bond_usdc": spec.bond_usdc,
            "total_funding_usdc": spec.total_funding_usdc,
            "verifier_type": spec.verifier_type,
        }
        print(json.dumps(seed_output, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(cli_main())
