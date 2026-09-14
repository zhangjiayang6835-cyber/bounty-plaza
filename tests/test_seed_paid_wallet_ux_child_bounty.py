"""Unit test suite for Paid Wallet UX Child Bounty Seeding Engine and Settlement Pipeline.
Tests Issue #816 requirements:
- Seeding and funding a concrete wallet UX coding bounty (0.90 USDC reward + 0.10 USDC bond).
- Verifier transition from unavailable/ready: false to ready: true upon funding.
- Distinct participant claiming with 0.10 USDC bond.
- Self-claim prohibition (creator cannot claim own seeded bounty).
- Deterministic Wallet UX verifier module execution (state coverage, chainId 8453, format_address, switch_network).
- Emission of canonical on-chain BountySettled receipt.
- Validates against Base mainnet discovery: 0xe8c1d3f046f3e4690bef59ba4abd5d02d2a6984b.
"""

import pytest
from scripts.seed_paid_wallet_ux_child_bounty import (
    BountyLifecycle,
    SeededWalletUXBountyHarness,
    WalletUXChildBountyConfig,
    WalletUXSpec,
)


@pytest.fixture
def sample_ux_harness():
    cfg = WalletUXChildBountyConfig(
        parent_discovery_id="eip155:8453:agent-bounties/autonomous-v1:0xe8c1d3f046f3e4690bef59ba4abd5d02d2a6984b",
        child_bounty_id="child_wallet_ux_001",
        contract_address="0xe8c1d3f046f3e4690bef59ba4abd5d02d2a6984b",
        network="base-mainnet",
        creator_address="0xCreatorBob222222222222222222222222222222222",
        solver_reward_usdc=0.90,
        claim_bond_usdc=0.10,
        total_funding_usdc=1.00,
        ux_spec=WalletUXSpec(
            target_chain_id=8453,
            required_states=[
                "disconnected",
                "connecting",
                "connected",
                "wrong_network",
                "signing",
                "confirmed",
            ],
            supported_connectors=["injected", "coinbase_wallet", "walletconnect"],
        ),
    )
    return SeededWalletUXBountyHarness(cfg)


def test_initial_state_unavailable_verifier_not_ready(sample_ux_harness):
    assert sample_ux_harness.lifecycle == BountyLifecycle.UNAVAILABLE
    assert sample_ux_harness.verifier_ready is False


def test_seed_and_fund_transitions_to_claimable_and_activates_verifier(sample_ux_harness):
    seed_res = sample_ux_harness.seed_and_fund(
        funder_address="0xCreatorBob222222222222222222222222222222222",
        funding_amount_usdc=1.00,
    )
    assert seed_res["status"] == "SEEDED_AND_FUNDED"
    assert sample_ux_harness.lifecycle == BountyLifecycle.CLAIMABLE
    assert sample_ux_harness.verifier_ready is True
    assert seed_res["funding_confirmed_usdc"] == 1.00


def test_creator_cannot_claim_own_seeded_bounty(sample_ux_harness):
    sample_ux_harness.seed_and_fund("0xCreatorBob222222222222222222222222222222222", 1.00)

    with pytest.raises(ValueError, match="Creator cannot claim their own seeded child bounty"):
        sample_ux_harness.claim_bounty(
            claimant_address="0xCreatorBob222222222222222222222222222222222",
            bond_deposit_usdc=0.10,
        )


def test_full_lifecycle_seed_claim_submit_and_canonical_settlement(sample_ux_harness):
    # 1. Seed & Fund
    sample_ux_harness.seed_and_fund("0xCreatorBob222222222222222222222222222222222", 1.00)

    # 2. Distinct participant claims with 0.10 USDC bond
    solver_dave = "0xSolverDave444444444444444444444444444444444"
    claim_res = sample_ux_harness.claim_bounty(solver_dave, bond_deposit_usdc=0.10)
    assert claim_res["status"] == "CLAIM_CONFIRMED"
    assert sample_ux_harness.lifecycle == BountyLifecycle.CLAIMED

    # 3. Solver submits valid Wallet UX implementation
    valid_ux_module = {
        "target_chain_id": 8453,
        "supported_states": [
            "disconnected",
            "connecting",
            "connected",
            "wrong_network",
            "signing",
            "confirmed",
        ],
        "format_address": lambda addr: f"{addr[:6]}...{addr[-4:]}",
        "switch_network": lambda chain_id: {"success": True, "current_chain_id": chain_id},
    }

    submit_res = sample_ux_harness.submit_solution(solver_dave, {"ux_module": valid_ux_module})
    assert submit_res["status"] == "SOLUTION_SUBMITTED"
    assert sample_ux_harness.lifecycle == BountyLifecycle.VERIFICATION_PENDING

    # 4. Verifier executes and produces canonical BountySettled receipt
    receipt = sample_ux_harness.verify_and_settle()
    assert receipt.canonical_event == "BountySettled"
    assert receipt.solver == solver_dave
    assert receipt.payout_usdc == 0.90
    assert receipt.bond_refunded_usdc == 0.10
    assert receipt.contract_address == "0xe8c1d3f046f3e4690bef59ba4abd5d02d2a6984b"
    assert receipt.tx_hash.startswith("0x")
    assert sample_ux_harness.lifecycle == BountyLifecycle.SETTLED


def test_verifier_fails_on_missing_required_state(sample_ux_harness):
    sample_ux_harness.seed_and_fund("0xCreatorBob222222222222222222222222222222222", 1.00)
    solver = "0xSolverDave444444444444444444444444444444444"
    sample_ux_harness.claim_bounty(solver, 0.10)

    # Missing "wrong_network" state
    incomplete_ux_module = {
        "target_chain_id": 8453,
        "supported_states": [
            "disconnected",
            "connecting",
            "connected",
            "signing",
            "confirmed",
        ],
        "format_address": lambda addr: f"{addr[:6]}...{addr[-4:]}",
        "switch_network": lambda chain_id: {"success": True, "current_chain_id": chain_id},
    }

    sample_ux_harness.submit_solution(solver, {"ux_module": incomplete_ux_module})

    with pytest.raises(ValueError, match="Wallet UX missing required state support: wrong_network"):
        sample_ux_harness.verify_and_settle()

    assert sample_ux_harness.lifecycle == BountyLifecycle.FAILED


def test_verifier_fails_on_wrong_chain_id(sample_ux_harness):
    sample_ux_harness.seed_and_fund("0xCreatorBob222222222222222222222222222222222", 1.00)
    solver = "0xSolverDave444444444444444444444444444444444"
    sample_ux_harness.claim_bounty(solver, 0.10)

    wrong_chain_ux_module = {
        "target_chain_id": 1,  # Ethereum mainnet instead of Base 8453
        "supported_states": [
            "disconnected",
            "connecting",
            "connected",
            "wrong_network",
            "signing",
            "confirmed",
        ],
        "format_address": lambda addr: f"{addr[:6]}...{addr[-4:]}",
        "switch_network": lambda chain_id: {"success": True, "current_chain_id": chain_id},
    }

    sample_ux_harness.submit_solution(solver, {"ux_module": wrong_chain_ux_module})

    with pytest.raises(ValueError, match="Chain ID mismatch: expected 8453, got 1"):
        sample_ux_harness.verify_and_settle()

    assert sample_ux_harness.lifecycle == BountyLifecycle.FAILED
