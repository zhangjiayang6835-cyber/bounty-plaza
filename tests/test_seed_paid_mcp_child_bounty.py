"""Unit test suite for Paid MCP Child Bounty Seeding Engine and Settlement Pipeline.
Tests Issue #818 requirements:
- Seeding and fully funding an MCP coding bounty (0.90 USDC reward + 0.10 USDC bond).
- Verifier transition from unavailable/ready: false to ready: true upon funding.
- A different registered participant claims the bounty with 0.10 USDC bond.
- Self-claim prohibition (creator cannot claim own seeded bounty).
- Deterministic MCP verifier module execution (tools/list, tools/call, query execution).
- Emission of canonical on-chain BountySettled receipt.
- Validates against Base mainnet discovery: 0x43d42cb227d76588ab16693f14efd6cff851fa7a.
"""

import pytest
from scripts.seed_paid_mcp_child_bounty import (
    BountyLifecycle,
    MCPChildBountyConfig,
    SeededMCPBountyHarness,
)


@pytest.fixture
def sample_harness():
    cfg = MCPChildBountyConfig(
        parent_discovery_id="eip155:8453:agent-bounties/autonomous-v1:0x43d42cb227d76588ab16693f14efd6cff851fa7a",
        child_bounty_id="child_mcp_sqlite_query_001",
        contract_address="0x43d42cb227d76588ab16693f14efd6cff851fa7a",
        network="base-mainnet",
        creator_address="0xCreatorAlice111111111111111111111111111111",
        solver_reward_usdc=0.90,
        claim_bond_usdc=0.10,
        total_funding_usdc=1.00,
    )
    return SeededMCPBountyHarness(cfg)


def test_initial_state_unavailable_verifier_not_ready(sample_harness):
    assert sample_harness.lifecycle == BountyLifecycle.UNAVAILABLE
    assert sample_harness.verifier_ready is False


def test_seed_and_fund_transitions_to_claimable_and_activates_verifier(sample_harness):
    seed_res = sample_harness.seed_and_fund(
        funder_address="0xCreatorAlice111111111111111111111111111111",
        funding_amount_usdc=1.00,
    )
    assert seed_res["status"] == "SEEDED_AND_FUNDED"
    assert sample_harness.lifecycle == BountyLifecycle.CLAIMABLE
    assert sample_harness.verifier_ready is True
    assert seed_res["funding_confirmed_usdc"] == 1.00


def test_creator_cannot_claim_own_seeded_bounty(sample_harness):
    sample_harness.seed_and_fund("0xCreatorAlice111111111111111111111111111111", 1.00)

    with pytest.raises(ValueError, match="Creator cannot claim their own seeded child bounty"):
        sample_harness.claim_bounty(
            claimant_address="0xCreatorAlice111111111111111111111111111111",
            bond_deposit_usdc=0.10,
        )


def test_full_lifecycle_seed_claim_submit_and_canonical_settlement(sample_harness):
    # 1. Seed and fund
    sample_harness.seed_and_fund("0xCreatorAlice111111111111111111111111111111", 1.00)

    # 2. Distinct participant claims with 0.10 USDC bond
    solver_bob = "0xSolverBob2222222222222222222222222222222222"
    claim_res = sample_harness.claim_bounty(solver_bob, bond_deposit_usdc=0.10)
    assert claim_res["status"] == "CLAIM_CONFIRMED"
    assert sample_harness.lifecycle == BountyLifecycle.CLAIMED

    # 3. Solver submits valid MCP solution payload
    valid_payload = {
        "name": "query_sqlite",
        "supported_methods": ["tools/list", "tools/call"],
        "execute_test_query": lambda q: {"rows": [{"num": 1}]},
    }
    submit_res = sample_harness.submit_solution(solver_bob, valid_payload)
    assert submit_res["status"] == "SOLUTION_SUBMITTED"
    assert sample_harness.lifecycle == BountyLifecycle.VERIFICATION_PENDING

    # 4. Verifier executes and produces canonical BountySettled receipt
    receipt = sample_harness.verify_and_settle()
    assert receipt.canonical_event == "BountySettled"
    assert receipt.solver == solver_bob
    assert receipt.payout_usdc == 0.90
    assert receipt.bond_refunded_usdc == 0.10
    assert receipt.contract_address == "0x43d42cb227d76588ab16693f14efd6cff851fa7a"
    assert receipt.tx_hash.startswith("0x")
    assert sample_harness.lifecycle == BountyLifecycle.SETTLED


def test_verifier_fails_on_invalid_mcp_tool_methods(sample_harness):
    sample_harness.seed_and_fund("0xCreatorAlice111111111111111111111111111111", 1.00)
    solver = "0xSolverBob2222222222222222222222222222222222"
    sample_harness.claim_bounty(solver, 0.10)

    # Missing tools/call
    invalid_payload = {
        "name": "query_sqlite",
        "supported_methods": ["tools/list"],
        "execute_test_query": lambda q: {"rows": []},
    }
    sample_harness.submit_solution(solver, invalid_payload)

    with pytest.raises(ValueError, match="Missing mandatory MCP JSON-RPC methods"):
        sample_harness.verify_and_settle()

    assert sample_harness.lifecycle == BountyLifecycle.FAILED
