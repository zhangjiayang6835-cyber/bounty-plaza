"""Command-line interface for Agent Bounties API child seeder."""

import argparse
import json
import sys
from typing import Optional
from packages.agent_bounties_api_seeder.models import (
    ApiEndpointSpec,
    ApiHttpMethod,
    ApiResponseTelemetry,
    DeterministicApiTaskVector,
    ParticipantRole,
    canonicalize_json_payload,
    compute_sha256_digest,
)
from packages.agent_bounties_api_seeder.seeder import ApiBountySeeder


def create_cli_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser for agent bounties seeder.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        description="Autonomous Agent Bounties API Child Seeder and Settlement Engine"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed_parser = subparsers.add_parser("seed", help="Seed a new child API coding bounty")
    seed_parser.add_argument("--parent", required=True, help="Parent bounty contract address")
    seed_parser.add_argument("--title", required=True, help="Task title")
    seed_parser.add_argument("--description", required=True, help="Task description")
    seed_parser.add_argument("--reward", type=float, default=0.90, help="Solver reward in USDC")
    seed_parser.add_argument("--bond", type=float, default=0.10, help="Solver bond in USDC")

    margin_parser = subparsers.add_parser("margin", help="Calculate economic margins")
    margin_parser.add_argument("--parent-reward", type=float, default=2.00)
    margin_parser.add_argument("--child-funding", type=float, default=1.00)

    demo_parser = subparsers.add_parser("demo", help="Run deterministic end-to-end simulation")
    demo_parser.add_argument("--parent", default="0xd15306a8cc4274ec46d913817ca4490c4fc41303")

    return parser


def run_demo(parent_address: str) -> dict[str, object]:
    """Execute end-to-end lifecycle demonstration and return verification payload.

    Args:
        parent_address: Parent bounty address.

    Returns:
        Dictionary containing verified simulation telemetry.
    """
    seeder = ApiBountySeeder()

    creator = "0x52513a733d4b52282f2b4f5a91d965d38b64f3bb"
    solver = "0x62f7793b28dfa508067b186144a23c49dd0bf02f"

    seeder.register_participant(creator, ParticipantRole.PARENT_CREATOR, timestamp=100)
    seeder.register_participant(solver, ParticipantRole.CHILD_SOLVER, timestamp=110)

    spec = seeder.publish_child_terms(
        parent_bounty_id=parent_address,
        title="API: High-Performance Deterministic Settlement Endpoint",
        description="Build deterministic REST API endpoint outputting settlement receipts.",
        reward_tuple=(0.90, 0.10),
        timestamp=120,
    )

    seeder.fund_child_escrow(spec.bounty_id, creator, amount_usdc=1.00, timestamp=130)
    seeder.claim_parent_bounty(
        parent_address, spec.bounty_id, creator, bond_usdc=0.01, timestamp=140
    )
    seeder.claim_child_bounty(spec.bounty_id, solver, bond_usdc=0.10, timestamp=150)

    payload_text = canonicalize_json_payload({
        "status": "success",
        "task_type": "api_settlement_service",
        "protocol_version": "v3",
        "block_height": 21890123,
    })
    expected_digest = compute_sha256_digest(payload_text)

    task_vector = DeterministicApiTaskVector(
        endpoint=ApiEndpointSpec(
            route="/v1/bounty/settle",
            method=ApiHttpMethod.POST,
            request_body='{"action":"verify_settlement"}',
        ),
        expected_status_code=200,
        expected_schema=("status", "task_type", "protocol_version", "block_height"),
        expected_response_digest=expected_digest,
        max_latency_ms=250.0,
    )

    receipt = seeder.record_api_execution(
        child_bounty_id=spec.bounty_id,
        solver_address=solver,
        telemetry=ApiResponseTelemetry(
            status_code=200,
            response_body=payload_text,
            response_digest=expected_digest,
            latency_ms=45.2,
        ),
        timestamp=160,
    )

    quorum, settlement, proof = seeder.settle_child_bounty(receipt, task_vector, timestamp=170)
    economics = seeder.calculate_economics()

    result: dict[str, object] = {
        "child_bounty_id": spec.bounty_id,
        "total_child_funding_usdc": spec.total_funding_usdc,
        "solver_payout_usdc": settlement.payout_usdc,
        "quorum_passed": quorum.passed,
        "encoded_abi_proof": proof.encoded_abi,
        "gross_profit_usdc": economics.gross_profit_usdc,
        "settlement_tx": settlement.transaction_hash,
    }
    return result


def main(argv: Optional[list[str]] = None) -> int:
    """Main CLI entrypoint.

    Args:
        argv: Optional argument list.

    Returns:
        Exit code integer.
    """
    parser = create_cli_parser()
    args = parser.parse_args(argv)

    if args.command == "margin":
        seeder = ApiBountySeeder()
        margin = seeder.calculate_economics(args.parent_reward, args.child_funding)
        print(f"Parent Reward: {margin.parent_reward_usdc:.2f} USDC")
        print(f"Child Funding: {margin.child_funding_usdc:.2f} USDC")
        print(f"Gross Profit:  {margin.gross_profit_usdc:.2f} USDC")
        print(f"Margin:        {margin.net_margin_percentage:.1f}%")
        return 0

    if args.command == "demo":
        demo_output = run_demo(args.parent)
        print(json.dumps(demo_output, indent=2))
        return 0

    if args.command == "seed":
        seeder = ApiBountySeeder()
        spec = seeder.publish_child_terms(
            parent_bounty_id=args.parent,
            title=args.title,
            description=args.description,
            reward_tuple=(args.reward, args.bond),
        )
        print(f"Seeded Child Bounty: {spec.bounty_id}")
        print(f"Total Target: {spec.total_funding_usdc:.2f} USDC")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
