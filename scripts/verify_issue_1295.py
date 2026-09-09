"""Verification entrypoint for Issue 1295 MCP child bounty seeder."""

import json
import sys
from packages.agent_bounties_mcp_seeder.cli import run_demo

EXPECTED_EVM = "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89"
EXPECTED_STELLAR = "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC"
DEFAULT_PARENT = "0x43d42cb227d76588ab16693f14efd6cff851fa7a"


def run_verification(parent_address: str = DEFAULT_PARENT) -> dict[str, object]:
    """Execute simulation and enforce strict protocol assertions.

    Args:
        parent_address: Parent coordination bounty contract address.

    Returns:
        Verified dictionary of telemetry and settlement proof.

    Raises:
        AssertionError: If any verification condition fails.
    """
    result = run_demo(parent_address)

    if result.get("status") != "success":
        raise AssertionError("Expected status success")

    if result.get("bounty_status") != "settled":
        raise AssertionError("Expected bounty_status settled")

    if result.get("quorum_passed") is not True:
        raise AssertionError("Expected quorum_passed to be True")

    if result.get("solver_payout_usdc") != 0.90:
        raise AssertionError("Expected solver_payout_usdc 0.90")

    if result.get("bond_refund_usdc") != 0.10:
        raise AssertionError("Expected bond_refund_usdc 0.10")

    if result.get("parent_reward_usdc") != 2.00:
        raise AssertionError("Expected parent_reward_usdc 2.00")

    if result.get("gross_profit_usdc") != 1.00:
        raise AssertionError("Expected gross_profit_usdc 1.00")

    if result.get("net_margin_percentage") != 50.0:
        raise AssertionError("Expected net_margin_percentage 50.0")

    encoded_proof = str(result.get("encoded_abi_proof", ""))
    if not encoded_proof.startswith("0x") or len(encoded_proof) != 66:
        raise AssertionError(f"Invalid ABI proof encoding: {encoded_proof}")

    if result.get("payout_routing_evm") != EXPECTED_EVM:
        raise AssertionError("Invalid EVM payout routing address")

    if result.get("payout_routing_stellar") != EXPECTED_STELLAR:
        raise AssertionError("Invalid Stellar payout routing address")

    return result


def main() -> int:
    """Execute verification and display JSON output to standard out.

    Returns:
        Exit code zero on success.
    """
    verification_data = run_verification()
    print(json.dumps(verification_data, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
