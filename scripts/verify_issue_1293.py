"""Verification runner for Issue 1293 API child bounty seeder."""

import json
import sys
from packages.agent_bounties_api_seeder.cli import run_demo


def run_verification() -> int:
    """Execute end-to-end verification and assert all protocol stipulations.

    Returns:
        0 on complete verification success, 1 on failure.
    """
    parent_address = "0xd15306a8cc4274ec46d913817ca4490c4fc41303"
    result = run_demo(parent_address)

    if not result.get("quorum_passed"):
        print("Verification failed: quorum did not pass")
        return 1

    if result.get("solver_payout_usdc") != 0.90:
        print("Verification failed: solver payout is not 0.90 USDC")
        return 1

    if result.get("gross_profit_usdc") != 1.00:
        print("Verification failed: gross profit is not 1.00 USDC")
        return 1

    abi_proof = str(result.get("encoded_abi_proof", ""))
    if not (abi_proof.startswith("0x") and len(abi_proof) == 66):
        print("Verification failed: ABI proof format invalid")
        return 1

    print("All Issue 1293 API child bounty stipulations verified.")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(run_verification())
