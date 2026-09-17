"""Tests for the direct-bounty verifier-readiness diagnostics (#734).

Covers the acceptance criteria:

1. API and MCP expose verifier set hash, threshold, runner identifier, and
   readiness.
2. Unready inventory has one concise reason and is excluded from ready-to-earn
   results.
3. Tests cover healthy, missing-signer, stale-runner, and verifier-set-mismatch
   states.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from verifier_readiness import (
    DiagnosticsMcp,
    RunnerInfo,
    VerifierService,
    VerifierSet,
    build_service_from_fixture,
)

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "verifier-readiness-fixture.json"
).resolve()

FIXTURE_JSON = json.loads(FIXTURE.read_text(encoding="utf-8"))
EXPECTED_HASH = FIXTURE_JSON["expected_hash"]
SERVICE = build_service_from_fixture(FIXTURE)

HEALTHY = "0xc710d54d192ffb0b84cd6e051754ab70acf1130c"
MISSING_SIGNER = "0xad4532e45d371ff5b5c40ebbf0c20687ed9e6fc4"
STALE_RUNNER = "0x0f1e2d3c4b5a697887766554433221100feedface"
MISMATCH = "0xdeadbeefcafebabe000000000000000000000000"
NO_RUNNER = "0x1111111111111111111111111111111111111111"
NO_CONFIG = "0x2222222222222222222222222222222222222222"


def test_healthy_verifier_state() -> None:
    """A healthy contract reports Ready with full diagnostics."""
    diagnostics = SERVICE.check_readiness(HEALTHY, EXPECTED_HASH)
    assert diagnostics.verifier_set_hash == EXPECTED_HASH
    assert diagnostics.threshold == 2
    assert diagnostics.runner_identifier == "sandboxed_regression_v1"
    assert diagnostics.is_ready() is True
    assert diagnostics.reason() is None


def test_missing_signer_state() -> None:
    """A contract with fewer signers than threshold is not ready."""
    diagnostics = SERVICE.check_readiness(MISSING_SIGNER, EXPECTED_HASH)
    assert diagnostics.threshold == 3
    assert diagnostics.is_ready() is False
    assert "signers available" in diagnostics.reason()


def test_stale_runner_state() -> None:
    """A runner that last checked in too long ago is stale."""
    diagnostics = SERVICE.check_readiness(STALE_RUNNER, EXPECTED_HASH)
    assert diagnostics.is_ready() is False
    assert "seconds ago" in diagnostics.reason()


def test_verifier_set_mismatch_state() -> None:
    """A mismatched verifier set hash is not ready."""
    diagnostics = SERVICE.check_readiness(MISMATCH, EXPECTED_HASH)
    assert diagnostics.verifier_set_hash != EXPECTED_HASH
    assert diagnostics.is_ready() is False
    assert "expected" in diagnostics.reason()


def test_no_runner_registered_fails_closed() -> None:
    """A verifier set without a registered runner is stale."""
    diagnostics = SERVICE.check_readiness(NO_RUNNER, EXPECTED_HASH)
    assert diagnostics.runner_identifier == "unknown"
    assert diagnostics.is_ready() is False
    assert diagnostics.reason() == "no runner registered"


def test_no_configuration_fails_closed() -> None:
    """No verifier configuration fails closed with mismatch."""
    diagnostics = SERVICE.check_readiness(NO_CONFIG, EXPECTED_HASH)
    assert diagnostics.verifier_set_hash == "unknown"
    assert diagnostics.threshold == 0
    assert diagnostics.is_ready() is False
    assert diagnostics.reason() == "no verifier configuration found"


def test_api_contract_status_exposes_diagnostics() -> None:
    """The API contract status exposes the full diagnostics block."""
    status = SERVICE.contract_status(HEALTHY, EXPECTED_HASH)
    assert status["contract"] == HEALTHY
    assert status["status"] == "claimable"
    diagnostics = status["diagnostics"]
    assert diagnostics["verifier_set_hash"] == EXPECTED_HASH
    assert diagnostics["threshold"] == 2
    assert diagnostics["runner_identifier"] == "sandboxed_regression_v1"
    assert diagnostics["readiness"] == "ready"
    assert diagnostics["is_ready"] is True


def test_api_list_bounties_ready_only_excludes_unready() -> None:
    """Ready-only listing excludes every unready contract."""
    contracts = (HEALTHY, MISSING_SIGNER, STALE_RUNNER, MISMATCH, NO_RUNNER, NO_CONFIG)
    ready_only = SERVICE.list_bounties(EXPECTED_HASH, contracts, ready_only=True)
    names = [entry["contract"] for entry in ready_only]
    assert names == [HEALTHY]
    for entry in ready_only:
        assert entry["diagnostics"]["is_ready"] is True


def test_api_list_bounties_all_includes_unready() -> None:
    """The full listing keeps unready contracts with one concise reason."""
    contracts = (HEALTHY, MISSING_SIGNER, STALE_RUNNER, MISMATCH)
    all_items = SERVICE.list_bounties(EXPECTED_HASH, contracts, ready_only=False)
    assert len(all_items) == 4
    for entry in all_items:
        if entry["contract"] != HEALTHY:
            assert entry["diagnostics"]["is_ready"] is False
            assert entry["diagnostics"]["reason"] is not None


def test_mcp_get_verifier_diagnostics() -> None:
    """The MCP surface exposes verifier set hash, threshold, runner, readiness."""
    mcp = DiagnosticsMcp(SERVICE)
    payload = mcp.get_verifier_diagnostics(HEALTHY, EXPECTED_HASH)
    for field in (
        "verifier_set_hash",
        "threshold",
        "runner_identifier",
        "readiness",
        "is_ready",
        "reason",
    ):
        assert field in payload
    assert payload["is_ready"] is True


def test_mcp_list_ready_bounties() -> None:
    """MCP list-ready returns only ready bounties."""
    mcp = DiagnosticsMcp(SERVICE)
    contracts = (HEALTHY, MISSING_SIGNER, STALE_RUNNER, MISMATCH)
    result = mcp.list_ready_bounties(EXPECTED_HASH, contracts)
    assert len(result["ready_bounties"]) == 1
    assert result["ready_bounties"][0]["contract"] == HEALTHY
    assert result["ready_bounties"][0]["diagnostics"]["readiness"] == "ready"


def test_ready_only_excludes_stale_runner() -> None:
    """Stale-runner inventory is excluded from ready-to-earn."""
    contracts = (STALE_RUNNER,)
    ready_only = SERVICE.list_bounties(EXPECTED_HASH, contracts, ready_only=True)
    assert ready_only == []


def test_ready_only_excludes_missing_signer() -> None:
    """Missing-signer inventory is excluded from ready-to-earn."""
    contracts = (MISSING_SIGNER,)
    ready_only = SERVICE.list_bounties(EXPECTED_HASH, contracts, ready_only=True)
    assert ready_only == []


def test_ready_only_excludes_mismatch() -> None:
    """Verifier-set-mismatch inventory is excluded from ready-to-earn."""
    contracts = (MISMATCH,)
    ready_only = SERVICE.list_bounties(EXPECTED_HASH, contracts, ready_only=True)
    assert ready_only == []


def test_fixture_expected_states_match_engine() -> None:
    """Every fixture contract resolves to its declared expected state."""
    expectations = {
        entry["contract"]: entry["expected_state"]
        for entry in FIXTURE_JSON["contracts"]
    }
    for contract, expected in expectations.items():
        diagnostics = SERVICE.check_readiness(contract, EXPECTED_HASH)
        if expected == "healthy":
            assert diagnostics.is_ready() is True
        elif expected == "missing_signer":
            assert diagnostics.readiness._state == "missing_signer"  # noqa: SLF001
        elif expected == "stale_runner":
            assert diagnostics.readiness._state == "stale_runner"  # noqa: SLF001
        elif expected == "verifier_set_mismatch":
            assert diagnostics.readiness._state == "verifier_set_mismatch"  # noqa: SLF001
        elif expected == "no_runner":
            assert diagnostics.reason() == "no runner registered"
        elif expected == "no_config":
            assert diagnostics.reason() == "no verifier configuration found"


def test_diagnostics_json_shape() -> None:
    """The diagnostics JSON shape is stable and complete."""
    diagnostics = SERVICE.check_readiness(HEALTHY, EXPECTED_HASH)
    payload = diagnostics.to_json()
    assert set(payload) == {
        "verifier_set_hash",
        "threshold",
        "runner_identifier",
        "readiness",
        "is_ready",
        "reason",
    }


def test_fresh_runner_with_sufficient_signers_is_ready() -> None:
    """A manually registered fresh runner with enough signers is ready."""
    service = VerifierService()
    contract = "0xtest123"
    now = int(time.time())
    service.register_verifier_set(
        contract,
        VerifierSet(
            hash=EXPECTED_HASH,
            threshold=2,
            signers=("0xsigner1", "0xsigner2"),
        ),
    )
    service.register_runner(
        contract,
        RunnerInfo(identifier="runner_v1", version="1.0.0", last_seen=now),
    )
    diagnostics = service.check_readiness(contract, EXPECTED_HASH, now=now)
    assert diagnostics.is_ready() is True
    assert diagnostics.runner_identifier == "runner_v1"


def test_signers_counted_below_threshold() -> None:
    """Signers below threshold yield MissingSigner."""
    service = VerifierService()
    contract = "0xtest456"
    now = int(time.time())
    service.register_verifier_set(
        contract,
        VerifierSet(hash=EXPECTED_HASH, threshold=3, signers=("0xsigner1",)),
    )
    service.register_runner(
        contract,
        RunnerInfo(identifier="runner_v1", version="1.0.0", last_seen=now),
    )
    diagnostics = service.check_readiness(contract, EXPECTED_HASH, now=now)
    assert diagnostics.is_ready() is False
    assert "signers available" in diagnostics.reason()
