"""Command-line interface for Agent Bounties CLI child seeder."""

import argparse
import json
import sys
from typing import Optional
from packages.agent_bounties_seeder.models import (
    DeterministicTaskVector,
    ParticipantRole,
    compute_sha256_digest,
)
from packages.agent_bounties_seeder.seeder import CLIBountySeeder


def create_cli_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser for agent bounties seeder.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        description="Autonomous Agent Bounties CLI Child Seeder and Settlement Engine"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed_parser = subparsers.add_parser("seed", help="Seed a new child CLI coding bounty")
    seed_parser.add_argument("--parent", required=True, help="Parent bounty contract address")
    seed_parser.add_argument("--title", required=True, help="Task title")
    seed_parser.add_argument("--description", required=True, help="Task description")
    seed_parser.add_argument("--reward", type=float, default=0.90, help="Solver reward in USDC")
    seed_parser.add_argument("--bond", type=float, default=0.10, help="Solver bond in USDC")

    margin_parser = subparsers.add_parser("margin", help="Calculate economic margins")
    margin_parser.add_argument("--parent-reward", type=float, default=2.00)
    margin_parser.add_argument("--child-funding", type=float, default=1.00)

    demo_parser = subparsers.add_parser("demo", help="Run deterministic end-to-end simulation")
    demo_parser.add_argument("--parent", default="0x7b056457d04bcdbb5851112d007168aba30adf49")

    return parser


def run_demo(parent_address: str) -> dict[str, object]:
    """Execute end-to-end lifecycle demonstration and return verification payload.

    Args:
        parent_address: Parent bounty address.

    Returns:
        Dictionary containing verified simulation telemetry.
    """
    seeder = CLIBountySeeder()

    parent_creator = "0x52513a733d4b52282f2b4f5a91d965d38b64f3bb"
    child_solver = "0x62f7793b28dfa508067b186144a23c49dd0bf02f"

    seeder.register_participant(parent_creator, ParticipantRole.PARENT_CREATOR, timestamp=100)
    seeder.register_participant(child_solver, ParticipantRole.CHILD_SOLVER, timestamp=110)

    spec = seeder.publish_child_terms(
        parent_bounty_id=parent_address,
        title="CLI: Implement Deterministic Module Verifier",
        description="Build deterministic CLI tool outputting verified schema.",
        reward_tuple=(0.90, 0.10),
        timestamp=120,
    )

    seeder.fund_child_escrow(
        child_bounty_id=spec.bounty_id,
        funder_address=parent_creator,
        amount_usdc=1.00,
        timestamp=130,
    )

    seeder.claim_parent_bounty(
        parent_bounty_id=parent_address,
        child_bounty_id=spec.bounty_id,
        claimer_address=parent_creator,
        bond_usdc=0.01,
        timestamp=140,
    )

    seeder.claim_child_bounty(
        child_bounty_id=spec.bounty_id,
        solver_address=child_solver,
        bond_usdc=0.10,
        timestamp=150,
    )

    payload_text = '{"status": "ok", "task": "deterministic_cli", "result": 42}'
    expected_digest = compute_sha256_digest(payload_text)
    task_vector = DeterministicTaskVector(
        command_name="bounty-verifier",
        arguments=("--mode", "deterministic"),
        expected_exit_code=0,
        expected_digest=expected_digest,
    )

    receipt = seeder.record_execution(
        child_bounty_id=spec.bounty_id,
        solver_address=child_solver,
        output_payload=payload_text,
        exit_code=0,
        timestamp=160,
    )

    quorum, settlement, proof = seeder.settle_child_bounty(
        receipt=receipt,
        task_vector=task_vector,
        timestamp=170,
    )

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
        seeder = CLIBountySeeder()
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
        seeder = CLIBountySeeder()
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
