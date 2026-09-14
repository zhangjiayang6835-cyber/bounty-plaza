"""Standalone verification script for Issue #1219 child bounty seeder."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from packages.wallet_ux_seeder import run_demo


def verify_issue_1219() -> int:
    """Execute end-to-end verification and confirm all payout stipulations.

    Returns:
        0 if all stipulations pass, non-zero otherwise.
    """
    demo = run_demo()

    assert demo["child_bounty_id"].startswith("0x"), "Child bounty ID must be valid EVM address"
    assert len(demo["child_bounty_id"]) == 42, "Child bounty address must be 20 bytes"
    assert demo["total_child_funding_usdc"] == 1.00, "Child funding must equal 1.00 USDC"
    assert demo["solver_payout_usdc"] == 0.90, "Solver reward must equal 0.90 USDC"
    assert demo["quorum_passed"] is True, "Verifier quorum must reach consensus"
    assert demo["quorum_threshold"] == 2, "Consensus threshold must equal 2 nodes"
    assert demo["transaction_hash"].startswith("0x"), "Must contain canonical transaction anchor"
    assert len(demo["encoded_parent_proof"]) == 66, "Parent proof must be 32-byte ABI word"
    assert demo["gross_profit_usdc"] == 1.00, "Retained gross profit must equal 1.00 USDC"
    assert demo["net_margin_percentage"] == 50.0, "Net margin must equal 50.0%"
    assert demo["payout_routing_evm"] == "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89", "EVM payout must match"
    assert demo["payout_routing_stellar"] == "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC", "Stellar payout must match"

    print("Issue #1219 Verification PASSED:")
    print(f"  Parent Bounty:     {demo['parent_bounty_id']}")
    print(f"  Child Bounty:      {demo['child_bounty_id']}")
    print(f"  Child Funding:     {demo['total_child_funding_usdc']:.2f} USDC")
    print(f"  Solver Payout:     {demo['solver_payout_usdc']:.2f} USDC")
    print(f"  Quorum Passed:     {demo['quorum_passed']} ({demo['quorum_threshold']}/2 nodes)")
    print(f"  Tx Hash Anchor:    {demo['transaction_hash']}")
    print(f"  ABI Proof Hex:     {demo['encoded_parent_proof']}")
    print(f"  Retained Profit:   {demo['gross_profit_usdc']:.2f} USDC ({demo['net_margin_percentage']:.1f}%)")
    print(f"  EVM Payout:        {demo['payout_routing_evm']}")
    print(f"  Stellar Payout:    {demo['payout_routing_stellar']}")
    return 0


if __name__ == "__main__":
    sys.exit(verify_issue_1219())
