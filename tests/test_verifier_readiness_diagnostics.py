"""Unit test suite for Verifier Readiness Diagnostics & Direct Seed Runner.
Tests Issue #734 requirements:
- API and MCP output expose verifier set hash, threshold, runner identifier, and readiness.
- Unready inventory provides one concise reason and is excluded from ready-to-earn results.
- Comprehensive test coverage for:
  1. Healthy, ready-for-bonding state.
  2. Missing signer (insufficient active signers for threshold).
  3. Stale runner heartbeat (> 120s or runner offline).
  4. Verifier set hash mismatch against on-chain committed hash.
- Validates against Base mainnet live payment contract: 0xc710d54d192ffb0b84cd6e051754ab70acf1130c.
"""

import time
import pytest
from scripts.verifier_readiness_diagnostics import (
    BountyDiagnosticCandidate,
    ReadinessState,
    RunnerIdentifier,
    VerifierDiagnosticResult,
    VerifierReadinessDiagnostics,
    VerifierSet,
)


@pytest.fixture
def sample_signers():
    return [
        "0x1111111111111111111111111111111111111111",
        "0x2222222222222222222222222222222222222222",
        "0x3333333333333333333333333333333333333333",
    ]


@pytest.fixture
def healthy_candidate(sample_signers):
    vset = VerifierSet(signers=sample_signers, threshold=2)
    expected_hash = vset.set_hash
    now = 1757000000.0
    runner = RunnerIdentifier(
        runner_id="sandboxed_regression_v1",
        runner_version="1.4.0",
        last_heartbeat_timestamp=now - 10.0,
        is_online=True,
    )
    return BountyDiagnosticCandidate(
        bounty_id="nspg13_direct_638",
        contract_address="0xc710d54d192ffb0b84cd6e051754ab70acf1130c",
        network="base-mainnet",
        payout_usdc=1.99,
        refundable_bond_usdc=0.01,
        verifier_set=vset,
        expected_verifier_set_hash=expected_hash,
        runner=runner,
        active_signer_pool=sample_signers,
        max_heartbeat_staleness_seconds=120.0,
    )


def test_healthy_candidate_is_ready_for_bonding(healthy_candidate):
    now = 1757000000.0
    diag = VerifierReadinessDiagnostics.evaluate_candidate(healthy_candidate, current_time=now)

    assert diag.is_ready is True
    assert diag.unready_reason is None
    assert diag.threshold == 2
    assert diag.runner_identifier == "sandboxed_regression_v1"
    assert diag.contract_address == "0xc710d54d192ffb0b84cd6e051754ab70acf1130c"

    # API Output format check
    api_res = diag.to_api_response()
    assert api_res["verifier"]["readiness"] == ReadinessState.READY.value
    assert api_res["verifier"]["is_ready"] is True
    assert api_res["verifier"]["set_hash"] == healthy_candidate.expected_verifier_set_hash

    # MCP Output format check
    mcp_res = diag.to_mcp_output()
    assert "READY TO EARN" in mcp_res["content"][0]["text"]
    assert "YES" in mcp_res["content"][0]["text"]


def test_unready_on_verifier_set_mismatch(healthy_candidate):
    now = 1757000000.0
    healthy_candidate.expected_verifier_set_hash = "0xdeadbeef00000000000000000000000000000000000000000000000000000000"

    diag = VerifierReadinessDiagnostics.evaluate_candidate(healthy_candidate, current_time=now)
    assert diag.is_ready is False
    assert diag.unready_reason == "VERIFIER_SET_HASH_MISMATCH"

    api_res = diag.to_api_response()
    assert api_res["verifier"]["readiness"] == ReadinessState.UNREADY.value
    assert api_res["verifier"]["unready_reason"] == "VERIFIER_SET_HASH_MISMATCH"


def test_unready_on_missing_or_insufficient_signers(healthy_candidate):
    now = 1757000000.0
    # Only 1 signer online out of threshold 2
    healthy_candidate.active_signer_pool = [healthy_candidate.verifier_set.signers[0]]

    diag = VerifierReadinessDiagnostics.evaluate_candidate(healthy_candidate, current_time=now)
    assert diag.is_ready is False
    assert diag.unready_reason == "INSUFFICIENT_ACTIVE_SIGNERS"


def test_unready_on_stale_runner_heartbeat(healthy_candidate):
    now = 1757000000.0
    # Last heartbeat was 200 seconds ago (> 120s max staleness)
    healthy_candidate.runner.last_heartbeat_timestamp = now - 200.0

    diag = VerifierReadinessDiagnostics.evaluate_candidate(healthy_candidate, current_time=now)
    assert diag.is_ready is False
    assert diag.unready_reason == "STALE_RUNNER_HEARTBEAT"


def test_unready_on_offline_runner(healthy_candidate):
    now = 1757000000.0
    healthy_candidate.runner.is_online = False

    diag = VerifierReadinessDiagnostics.evaluate_candidate(healthy_candidate, current_time=now)
    assert diag.is_ready is False
    assert diag.unready_reason == "STALE_RUNNER_HEARTBEAT"


def test_filter_ready_to_earn_inventory(healthy_candidate):
    now = 1757000000.0
    # Candidate 1: Healthy
    c1 = healthy_candidate

    # Candidate 2: Stale runner
    vset2 = VerifierSet(signers=healthy_candidate.verifier_set.signers, threshold=2)
    c2 = BountyDiagnosticCandidate(
        bounty_id="c2_stale",
        contract_address="0x222",
        network="base-mainnet",
        payout_usdc=1.99,
        refundable_bond_usdc=0.01,
        verifier_set=vset2,
        expected_verifier_set_hash=vset2.set_hash,
        runner=RunnerIdentifier(last_heartbeat_timestamp=now - 500.0),
        active_signer_pool=healthy_candidate.verifier_set.signers,
    )

    inventory = [c1, c2]
    ready_items = VerifierReadinessDiagnostics.filter_ready_to_earn(inventory, current_time=now)

    assert len(ready_items) == 1
    assert ready_items[0].bounty_id == "nspg13_direct_638"
    assert ready_items[0].contract_address == "0xc710d54d192ffb0b84cd6e051754ab70acf1130c"
