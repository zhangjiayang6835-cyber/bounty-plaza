"""Verification script for Issue #1291 Agent Bounties CLI child seeder."""

import sys
from packages.agent_bounties_seeder.cli import run_demo
from packages.agent_bounties_seeder.seeder import CLIBountySeeder


def verify_issue_1291() -> int:
    """Execute end-to-end verification of CLI child bounty lifecycle.

    Returns:
        0 on success, 1 on failure.
    """
    demo_result = run_demo("0x7b056457d04bcdbb5851112d007168aba30adf49")

    valid = True
    if demo_result.get("total_child_funding_usdc") != 1.00:
        valid = False
    if demo_result.get("solver_payout_usdc") != 0.90:
        valid = False
    if demo_result.get("quorum_passed") is not True:
        valid = False
    if demo_result.get("gross_profit_usdc") != 1.00:
        valid = False

    seeder = CLIBountySeeder()
    economics = seeder.calculate_economics()
    if economics.gross_profit_usdc < 1.00:
        valid = False

    return 0 if valid else 1


def main() -> int:
    """Main execution function.

    Returns:
        Process exit code.
    """
    result = verify_issue_1291()
    return result


if __name__ == "__main__":
    sys.exit(main())
