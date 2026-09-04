"""Unit test suite for Paid REST API Child Bounty Seeding Engine and Settlement Pipeline.
Tests Issue #817 requirements:
- Seeding and fully funding an API coding bounty (0.90 USDC reward + 0.10 USDC bond).
- Verifier transition from unavailable/ready: false to ready: true upon funding.
- A different registered participant claims the bounty with 0.10 USDC bond.
- Self-claim prohibition (creator cannot claim own seeded bounty).
- Deterministic API verifier module execution (route matching, status code 200, JSON schema).
- Emission of canonical on-chain BountySettled receipt.
- Validates against Base mainnet discovery: 0xbe17ef2d154265ebe3142d7bda5e99610d571455.
"""

import pytest
from scripts.seed_paid_api_child_bounty import (
    APIChildBountyConfig,
    APIEndpointSpec,
    BountyLifecycle,
    SeededAPIBountyHarness,
)


@pytest.fixture
def sample_api_harness():
    cfg = APIChildBountyConfig(
        parent_discovery_id="eip155:8453:agent-bounties/autonomous-v1:0xbe17ef2d154265ebe3142d7bda5e99610d571455",
        child_bounty_id="child_api_metrics_001",
        contract_address="0xbe17ef2d154265ebe3142d7bda5e99610d571455",
        network="base-mainnet",
        creator_address="0xCreatorAlice111111111111111111111111111111",
        solver_reward_usdc=0.90,
        claim_bond_usdc=0.10,
        total_funding_usdc=1.00,
        endpoint_spec=APIEndpointSpec(
            path="/api/v1/metrics",
            method="GET",
            expected_status_code=200,
            required_response_fields=["uptime_seconds", "active_connections", "healthy"],
        ),
    )
    return SeededAPIBountyHarness(cfg)


def test_initial_state_unavailable_verifier_not_ready(sample_api_harness):
    assert sample_api_harness.lifecycle == BountyLifecycle.UNAVAILABLE
    assert sample_api_harness.verifier_ready is False


def test_seed_and_fund_transitions_to_claimable_and_activates_verifier(sample_api_harness):
    seed_res = sample_api_harness.seed_and_fund(
        funder_address="0xCreatorAlice111111111111111111111111111111",
        funding_amount_usdc=1.00,
    )
    assert seed_res["status"] == "SEEDED_AND_FUNDED"
    assert sample_api_harness.lifecycle == BountyLifecycle.CLAIMABLE
    assert sample_api_harness.verifier_ready is True
    assert seed_res["funding_confirmed_usdc"] == 1.00


def test_creator_cannot_claim_own_seeded_bounty(sample_api_harness):
    sample_api_harness.seed_and_fund("0xCreatorAlice111111111111111111111111111111", 1.00)

    with pytest.raises(ValueError, match="Creator cannot claim their own seeded child bounty"):
        sample_api_harness.claim_bounty(
            claimant_address="0xCreatorAlice111111111111111111111111111111",
            bond_deposit_usdc=0.10,
        )


def test_full_lifecycle_seed_claim_submit_and_canonical_settlement(sample_api_harness):
    # 1. Seed and fund
    sample_api_harness.seed_and_fund("0xCreatorAlice111111111111111111111111111111", 1.00)

    # 2. Distinct participant claims with 0.10 USDC bond
    solver_charlie = "0xSolverCharlie3333333333333333333333333333333"
    claim_res = sample_api_harness.claim_bounty(solver_charlie, bond_deposit_usdc=0.10)
    assert claim_res["status"] == "CLAIM_CONFIRMED"
    assert sample_api_harness.lifecycle == BountyLifecycle.CLAIMED

    # 3. Solver submits valid API handler payload
    def mock_metrics_handler(request):
        return {
            "status_code": 200,
            "body": {
                "uptime_seconds": 3600,
                "active_connections": 42,
                "healthy": True,
            },
        }

    valid_payload = {
        "routes": ["/api/v1/metrics", "/api/v1/health"],
        "handler": mock_metrics_handler,
    }

    submit_res = sample_api_harness.submit_solution(solver_charlie, valid_payload)
    assert submit_res["status"] == "SOLUTION_SUBMITTED"
    assert sample_api_harness.lifecycle == BountyLifecycle.VERIFICATION_PENDING

    # 4. Verifier executes and produces canonical BountySettled receipt
    receipt = sample_api_harness.verify_and_settle()
    assert receipt.canonical_event == "BountySettled"
    assert receipt.solver == solver_charlie
    assert receipt.payout_usdc == 0.90
    assert receipt.bond_refunded_usdc == 0.10
    assert receipt.contract_address == "0xbe17ef2d154265ebe3142d7bda5e99610d571455"
    assert receipt.tx_hash.startswith("0x")
    assert sample_api_harness.lifecycle == BountyLifecycle.SETTLED


def test_verifier_fails_on_missing_required_schema_fields(sample_api_harness):
    sample_api_harness.seed_and_fund("0xCreatorAlice111111111111111111111111111111", 1.00)
    solver = "0xSolverCharlie3333333333333333333333333333333"
    sample_api_harness.claim_bounty(solver, 0.10)

    # Missing "healthy" field
    def defective_handler(request):
        return {
            "status_code": 200,
            "body": {
                "uptime_seconds": 120,
                "active_connections": 5,
            },
        }

    invalid_payload = {
        "routes": ["/api/v1/metrics"],
        "handler": defective_handler,
    }
    sample_api_harness.submit_solution(solver, invalid_payload)

    with pytest.raises(ValueError, match="Response missing required JSON field: healthy"):
        sample_api_harness.verify_and_settle()

    assert sample_api_harness.lifecycle == BountyLifecycle.FAILED
