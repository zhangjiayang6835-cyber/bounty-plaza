"""Command-line interface and demonstration runner for API child bounty seeder."""

import argparse
import json
import sys
from typing import Any, Sequence
from packages.api_child_bounty_seeder.models import (
    APIActionType,
    APIEndpointSpec,
    APITaskVector,
    ParticipantRole,
    compute_sha256_digest,
)
from packages.api_child_bounty_seeder.seeder import (
    APIBountySeeder,
    DEFAULT_PARENT_BOUNTY_ID,
)


def run_demo(parent_bounty_id: str = DEFAULT_PARENT_BOUNTY_ID) -> dict[str, Any]:
    """Execute end-to-end demonstration of child API bounty lifecycle.

    Args:
        parent_bounty_id: Parent bounty contract address on Base network.

    Returns:
        Structured dictionary recording state transitions and settlement proof.
    """
    seeder = APIBountySeeder()

    creator_addr = "0x7b056457d04bcdbb5851112d007168aba30adf49"
    solver_addr = "0x95222290dd7278aa3ddd389cc1e1d165cc4bafe5"
    t0 = 1728000000

    seeder.register_participant(creator_addr, ParticipantRole.PARENT_CREATOR, t0)
    seeder.register_participant(solver_addr, ParticipantRole.CHILD_SOLVER, t0 + 10)

    payload = json.dumps(
        {
            "action": "SETTLE_PAYMENT",
            "endpoint": "/v1/settlement/canonical",
            "response": "SETTLED",
            "status": "200_OK",
        },
        sort_keys=True,
    )

    task_vector = APITaskVector(
        endpoint=APIEndpointSpec(
            endpoint_id="api-canonical-settlement-endpoint",
            route_path="/v1/settlement/canonical",
            http_method="POST",
            action_type=APIActionType.SETTLE_PAYMENT,
            required_headers=("Content-Type", "Authorization", "X-Signature"),
        ),
        test_runner="pytest-api-harness",
        arguments=("--spec=/v1/settlement/canonical", "--strict-schema"),
        expected_status_code=200,
        expected_digest=compute_sha256_digest(payload),
    )

    spec = seeder.publish_child_terms(
        parent_bounty_id=parent_bounty_id,
        title="API Canonical Settlement Endpoint",
        description="Implement deterministic canonical API settlement receiver and validator",
        timestamp=t0 + 20,
    )

    seeder.fund_child_escrow(spec.bounty_id, creator_addr, 1.00, t0 + 30)
    seeder.claim_parent_bounty(parent_bounty_id, spec.bounty_id, creator_addr, 0.01, t0 + 40)
    seeder.claim_child_bounty(spec.bounty_id, solver_addr, 0.10, t0 + 50)

    receipt = seeder.record_execution(spec.bounty_id, solver_addr, payload, 200, t0 + 60)
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
    """Main CLI entrypoint for child API bounty orchestration.

    Args:
        args: Command-line arguments.

    Returns:
        0 on success, non-zero on failure.
    """
    parser = argparse.ArgumentParser(
        description="Autonomous API Child Bounty Seeder CLI"
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
        default="API Canonical Settlement Endpoint",
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
        seeder = APIBountySeeder()
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
        seeder = APIBountySeeder()
        spec = seeder.publish_child_terms(
            parent_bounty_id=parsed.parent_bounty,
            title=parsed.title,
            description="Autonomous deterministic API child bounty",
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
