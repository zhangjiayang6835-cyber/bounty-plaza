"""Unit test suite for Paid CLI Child Bounty Seeding Engine and Settlement Pipeline.
Tests Issue #815 requirements:
- Seeding and funding a concrete CLI coding bounty (0.90 USDC reward + 0.10 USDC bond).
- Verifier transition from unavailable/ready: false to ready: true upon funding.
- Distinct participant claiming with 0.10 USDC bond.
- Self-claim prohibition (creator cannot claim own seeded bounty).
- Deterministic CLI verifier module execution (help flags, subcommands, JSON formatting, non-zero errors).
- Emission of canonical on-chain BountySettled receipt.
- Validates against Base mainnet discovery: 0xfffecb0fcd36477c5f6ecec808f6f0cf53819562.
"""

import pytest
from scripts.seed_paid_cli_child_bounty import (
    BountyLifecycle,
    CLIChildBountyConfig,
    CLISpec,
    SeededCLIBountyHarness,
)


@pytest.fixture
def sample_cli_harness():
    cfg = CLIChildBountyConfig(
        parent_discovery_id="eip155:8453:agent-bounties/autonomous-v1:0xfffecb0fcd36477c5f6ecec808f6f0cf53819562",
        child_bounty_id="child_cli_suite_001",
        contract_address="0xfffecb0fcd36477c5f6ecec808f6f0cf53819562",
        network="base-mainnet",
        creator_address="0xCreatorEve555555555555555555555555555555555",
        solver_reward_usdc=0.90,
        claim_bond_usdc=0.10,
        total_funding_usdc=1.00,
        cli_spec=CLISpec(
            subcommands=["list", "inspect", "claim", "submit", "status"],
            supported_flags=["--json", "--network", "--help"],
            default_network="base-mainnet",
        ),
    )
    return SeededCLIBountyHarness(cfg)


def test_initial_state_unavailable_verifier_not_ready(sample_cli_harness):
    assert sample_cli_harness.lifecycle == BountyLifecycle.UNAVAILABLE
    assert sample_cli_harness.verifier_ready is False


def test_seed_and_fund_transitions_to_claimable_and_activates_verifier(sample_cli_harness):
    seed_res = sample_cli_harness.seed_and_fund(
        funder_address="0xCreatorEve555555555555555555555555555555555",
        funding_amount_usdc=1.00,
    )
    assert seed_res["status"] == "SEEDED_AND_FUNDED"
    assert sample_cli_harness.lifecycle == BountyLifecycle.CLAIMABLE
    assert sample_cli_harness.verifier_ready is True
    assert seed_res["funding_confirmed_usdc"] == 1.00


def test_creator_cannot_claim_own_seeded_bounty(sample_cli_harness):
    sample_cli_harness.seed_and_fund("0xCreatorEve555555555555555555555555555555555", 1.00)

    with pytest.raises(ValueError, match="Creator cannot claim their own seeded child bounty"):
        sample_cli_harness.claim_bounty(
            claimant_address="0xCreatorEve555555555555555555555555555555555",
            bond_deposit_usdc=0.10,
        )


def test_full_lifecycle_seed_claim_submit_and_canonical_settlement(sample_cli_harness):
    # 1. Seed & Fund
    sample_cli_harness.seed_and_fund("0xCreatorEve555555555555555555555555555555555", 1.00)

    # 2. Distinct participant claims with 0.10 USDC bond
    solver_frank = "0xSolverFrank66666666666666666666666666666666"
    claim_res = sample_cli_harness.claim_bounty(solver_frank, bond_deposit_usdc=0.10)
    assert claim_res["status"] == "CLAIM_CONFIRMED"
    assert sample_cli_harness.lifecycle == BountyLifecycle.CLAIMED

    # 3. Solver submits valid CLI tool implementation
    def mock_cli(args):
        if "--help" in args:
            return {"exit_code": 0, "stdout": "Usage: agent-bounties [COMMAND] [OPTIONS]"}
        cmd = args[0] if args else ""
        if cmd in ["list", "inspect", "claim", "submit", "status"]:
            return {
                "exit_code": 0,
                "stdout": '{"status": "ok"}',
                "json": {"cmd": cmd, "status": "ok", "items": []},
            }
        return {"exit_code": 1, "stderr": f"Unknown command: {cmd}"}

    submit_res = sample_cli_harness.submit_solution(solver_frank, {"cli_executor": mock_cli})
    assert submit_res["status"] == "SOLUTION_SUBMITTED"
    assert sample_cli_harness.lifecycle == BountyLifecycle.VERIFICATION_PENDING

    # 4. Verifier executes and produces canonical BountySettled receipt
    receipt = sample_cli_harness.verify_and_settle()
    assert receipt.canonical_event == "BountySettled"
    assert receipt.solver == solver_frank
    assert receipt.payout_usdc == 0.90
    assert receipt.bond_refunded_usdc == 0.10
    assert receipt.contract_address == "0xfffecb0fcd36477c5f6ecec808f6f0cf53819562"
    assert receipt.tx_hash.startswith("0x")
    assert sample_cli_harness.lifecycle == BountyLifecycle.SETTLED


def test_verifier_fails_on_broken_help_command(sample_cli_harness):
    sample_cli_harness.seed_and_fund("0xCreatorEve555555555555555555555555555555555", 1.00)
    solver = "0xSolverFrank66666666666666666666666666666666"
    sample_cli_harness.claim_bounty(solver, 0.10)

    # Broken help
    def defective_cli(args):
        if "--help" in args:
            return {"exit_code": 1, "stdout": "Error"}
        return {"exit_code": 0, "json": {}}

    sample_cli_harness.submit_solution(solver, {"cli_executor": defective_cli})

    with pytest.raises(ValueError, match="CLI failed to return 0 on --help with usage guide"):
        sample_cli_harness.verify_and_settle()

    assert sample_cli_harness.lifecycle == BountyLifecycle.FAILED


def test_verifier_fails_on_missing_subcommand_json_output(sample_cli_harness):
    sample_cli_harness.seed_and_fund("0xCreatorEve555555555555555555555555555555555", 1.00)
    solver = "0xSolverFrank66666666666666666666666666666666"
    sample_cli_harness.claim_bounty(solver, 0.10)

    def text_only_cli(args):
        if "--help" in args:
            return {"exit_code": 0, "stdout": "Usage: agent-bounties"}
        return {"exit_code": 0, "stdout": "Plain text output without json structure"}

    sample_cli_harness.submit_solution(solver, {"cli_executor": text_only_cli})

    with pytest.raises(ValueError, match="CLI subcommand 'list' did not output valid parsed JSON payload"):
        sample_cli_harness.verify_and_settle()

    assert sample_cli_harness.lifecycle == BountyLifecycle.FAILED
