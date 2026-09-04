"""Unit test suite for Lifecycle-Aware Activation Reconciliation Engine.
Tests Issue #735 requirements:
- Models canonical factory and hosted feed state for all four active statuses:
  claimable, claimed, submitted, and verifying.
- Proves no planner or send path runs for an already-canonical contract across all 4 active states.
- Proves invalid terms, unavailable verification, terminal failure, and ambiguity fail closed.
- Validates against Base mainnet live payment contract: 0x2afb91d160200fac4b91e6134b2cc9d9bff86f42.
"""

import pytest
from scripts.lifecycle_activation_reconciliation import (
    ACTIVE_LIFECYCLE_STATUSES,
    ActivationReconciliationEngine,
    LifecycleStatus,
    OnChainBountyContract,
)


@pytest.fixture
def live_contract():
    return OnChainBountyContract(
        contract_address="0x2afb91d160200fac4b91e6134b2cc9d9bff86f42",
        discovery_id="eip155:8453:agent-bounties/direct-v1:0x2afb91d160200fac4b91e6134b2cc9d9bff86f42",
        network="base-mainnet",
        status=LifecycleStatus.CLAIMABLE,
        confirmed_funding_usdc=2.00,
        required_funding_usdc=2.00,
        terms_valid=True,
        verifier_available=True,
    )


def test_no_planner_or_send_path_runs_for_all_four_active_statuses(live_contract):
    """Acceptance criterion: Verify that for an already-canonical contract,

    none of the 4 active statuses (claimable, claimed, submitted, verifying)
    triggers the planner or send path.
    """
    for status in ACTIVE_LIFECYCLE_STATUSES:
        engine = ActivationReconciliationEngine()
        live_contract.status = status
        engine.register_canonical_contract(live_contract)

        decision = engine.reconcile_activation(live_contract.discovery_id)

        assert decision.planner_triggered is False, f"Planner ran for status {status.value}"
        assert decision.send_path_executed is False, f"Send path executed for status {status.value}"
        assert decision.fail_closed is False
        assert decision.status == status.value
        assert decision.contract_address == live_contract.contract_address
        assert f"RESUME_{status.name}_LIFECYCLE" == decision.action
        assert engine.planner_runs == 0
        assert engine.send_tx_count == 0


def test_fail_closed_on_invalid_terms(live_contract):
    """Acceptance criterion: Invalid terms must fail closed."""
    engine = ActivationReconciliationEngine()
    live_contract.terms_valid = False
    engine.register_canonical_contract(live_contract)

    decision = engine.reconcile_activation(live_contract.discovery_id)
    assert decision.fail_closed is True
    assert decision.status == "FAIL_CLOSED"
    assert decision.planner_triggered is False
    assert decision.send_path_executed is False
    assert "Invalid terms" in decision.reason


def test_fail_closed_on_unavailable_verification(live_contract):
    """Acceptance criterion: Unavailable verification must fail closed."""
    engine = ActivationReconciliationEngine()
    live_contract.verifier_available = False
    engine.register_canonical_contract(live_contract)

    decision = engine.reconcile_activation(live_contract.discovery_id)
    assert decision.fail_closed is True
    assert decision.status == "FAIL_CLOSED"
    assert decision.planner_triggered is False
    assert decision.send_path_executed is False
    assert "Verifier suite unavailable" in decision.reason


def test_fail_closed_on_terminal_failure(live_contract):
    """Acceptance criterion: Terminal failure must fail closed."""
    engine = ActivationReconciliationEngine()
    live_contract.terminal_failure = True
    engine.register_canonical_contract(live_contract)

    decision = engine.reconcile_activation(live_contract.discovery_id)
    assert decision.fail_closed is True
    assert decision.status == "FAIL_CLOSED"
    assert decision.planner_triggered is False
    assert decision.send_path_executed is False
    assert "Terminal contract failure" in decision.reason


def test_fail_closed_on_ambiguity(live_contract):
    """Acceptance criterion: Ambiguity must fail closed."""
    engine = ActivationReconciliationEngine()
    live_contract.is_ambiguous = True
    engine.register_canonical_contract(live_contract)

    decision = engine.reconcile_activation(live_contract.discovery_id)
    assert decision.fail_closed is True
    assert decision.status == "FAIL_CLOSED"
    assert decision.planner_triggered is False
    assert decision.send_path_executed is False
    assert "Ambiguous state" in decision.reason


def test_clean_deployment_for_unregistered_bounty():
    """Confirms that only truly novel, un-instantiated bounties trigger the deployment path."""
    engine = ActivationReconciliationEngine()
    decision = engine.reconcile_activation("eip155:8453:agent-bounties/direct-v1:0xNewBounty")

    assert decision.action == "DEPLOY_NEW_CONTRACT"
    assert decision.planner_triggered is True
    assert decision.send_path_executed is True
    assert engine.planner_runs == 1
    assert engine.send_tx_count == 1
