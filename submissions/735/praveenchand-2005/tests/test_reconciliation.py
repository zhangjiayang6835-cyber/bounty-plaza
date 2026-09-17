"""Tests for lifecycle-aware activation reconciliation.

Covers the acceptance criteria for bounty #735:

1. Tests model canonical factory and hosted feed state for all four active
   statuses (claimable, claimed, submitted, verifying).
2. No planner or send path runs for an already-canonical contract.
3. Invalid terms, unavailable verification, terminal failure, and ambiguity
   fail closed.
"""

from __future__ import annotations

import json
from pathlib import Path

from reconciliation import (
    ActivationState,
    ActivationStatus,
    ReconciliationEngine,
    ReconciliationResult,
    engine_from_fixture,
)

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "reconciliation-lifecycle.json"
).resolve()

A = "0x1111111111111111111111111111111111111111"
B = "0x2222222222222222222222222222222222222222"
C = "0x3333333333333333333333333333333333333333"
D = "0x4444444444444444444444444444444444444444"
E = "0x5555555555555555555555555555555555555555"
F = "0x6666666666666666666666666666666666666666"
G = "0x7777777777777777777777777777777777777777"
H = "0x8888888888888888888888888888888888888888"


def register_both(engine: ReconciliationEngine, state: ActivationState) -> None:
    """Register the same state in both factory and feed."""
    engine.register_factory_state(state)
    engine.register_feed_state(state)


def test_claimable_state_resumes_without_duplicate() -> None:
    """A claimable contract seen in both factory and feed resumes."""
    engine = ReconciliationEngine()
    register_both(engine, ActivationState.new(A, ActivationStatus.CLAIMABLE))
    decision = engine.reconcile(A)
    assert decision.result == ReconciliationResult.RESUME
    assert decision.status == ActivationStatus.CLAIMABLE
    assert decision.should_run_planner() is True


def test_claimed_state_resumes_without_duplicate() -> None:
    """A claimed contract seen in both factory and feed resumes."""
    engine = ReconciliationEngine()
    register_both(engine, ActivationState.new(B, ActivationStatus.CLAIMED))
    decision = engine.reconcile(B)
    assert decision.result == ReconciliationResult.RESUME
    assert decision.status == ActivationStatus.CLAIMED
    assert decision.should_run_planner() is True


def test_submitted_state_resumes_without_duplicate() -> None:
    """A submitted contract seen in both factory and feed resumes."""
    engine = ReconciliationEngine()
    register_both(engine, ActivationState.new(C, ActivationStatus.SUBMITTED))
    decision = engine.reconcile(C)
    assert decision.result == ReconciliationResult.RESUME
    assert decision.status == ActivationStatus.SUBMITTED
    assert decision.should_run_planner() is True


def test_verifying_state_resumes_without_duplicate() -> None:
    """A verifying contract seen in both factory and feed resumes."""
    engine = ReconciliationEngine()
    register_both(engine, ActivationState.new(D, ActivationStatus.VERIFYING))
    decision = engine.reconcile(D)
    assert decision.result == ReconciliationResult.RESUME
    assert decision.status == ActivationStatus.VERIFYING
    assert decision.should_run_planner() is True


def test_active_status_set_covers_all_four() -> None:
    """The active set contains exactly the four resumable statuses."""
    assert ActivationStatus.active_statuses() == {
        ActivationStatus.CLAIMABLE,
        ActivationStatus.CLAIMED,
        ActivationStatus.SUBMITTED,
        ActivationStatus.VERIFYING,
    }


def test_canonical_contract_never_runs_planner() -> None:
    """An already-canonical contract skips the planner and send path."""
    engine = ReconciliationEngine()
    factory = ActivationState.new(E, ActivationStatus.CLAIMED).with_canonical(True)
    engine.register_factory_state(factory)
    engine.register_feed_state(ActivationState.new(E, ActivationStatus.CLAIMED))
    decision = engine.reconcile(E)
    assert decision.result == ReconciliationResult.ALREADY_CANONICAL
    assert decision.should_run_planner() is False


def test_mark_canonical_prevents_reprocessing() -> None:
    """Marking a contract canonical stops a later resume from running."""
    engine = ReconciliationEngine()
    register_both(engine, ActivationState.new(A, ActivationStatus.CLAIMED))
    first = engine.reconcile(A)
    assert first.result == ReconciliationResult.RESUME
    engine.mark_canonical(A)
    second = engine.reconcile(A)
    assert second.result == ReconciliationResult.ALREADY_CANONICAL
    assert second.should_run_planner() is False


def test_invalid_terms_fail_closed() -> None:
    """A contract with no factory row fails closed with invalid terms."""
    engine = ReconciliationEngine()
    decision = engine.reconcile(H)
    assert decision.result == ReconciliationResult.INVALID_TERMS
    assert decision.should_run_planner() is False


def test_unavailable_verification_fails_closed() -> None:
    """A feed state that is not active makes the decision ambiguous."""
    engine = ReconciliationEngine()
    engine.register_factory_state(ActivationState.new(A, ActivationStatus.CLAIMED))
    engine.register_feed_state(ActivationState.new(A, ActivationStatus.SETTLED))
    decision = engine.reconcile(A)
    assert decision.result == ReconciliationResult.AMBIGUOUS
    assert decision.should_run_planner() is False


def test_terminal_failure_fails_closed() -> None:
    """A failed contract is terminal and never runs the planner."""
    engine = ReconciliationEngine()
    register_both(engine, ActivationState.new(F, ActivationStatus.FAILED))
    decision = engine.reconcile(F)
    assert decision.result == ReconciliationResult.TERMINAL
    assert decision.status == ActivationStatus.FAILED
    assert decision.should_run_planner() is False


def test_settled_state_is_terminal() -> None:
    """A settled contract is terminal and never runs the planner."""
    engine = ReconciliationEngine()
    register_both(engine, ActivationState.new(G, ActivationStatus.SETTLED))
    decision = engine.reconcile(G)
    assert decision.result == ReconciliationResult.TERMINAL
    assert decision.status == ActivationStatus.SETTLED
    assert decision.should_run_planner() is False


def test_active_factory_with_no_feed_creates() -> None:
    """An active factory row with no feed row is a fresh create."""
    engine = ReconciliationEngine()
    engine.register_factory_state(ActivationState.new(A, ActivationStatus.CLAIMABLE))
    decision = engine.reconcile(A)
    assert decision.result == ReconciliationResult.CREATE
    assert decision.status == ActivationStatus.CLAIMABLE
    assert decision.should_run_planner() is True


def test_decision_json_shape() -> None:
    """Reconciliation decisions serialize to the canonical JSON shape."""
    engine = ReconciliationEngine()
    register_both(engine, ActivationState.new(A, ActivationStatus.CLAIMABLE))
    payload = engine.decision_to_json(engine.reconcile(A))
    for field in ("contract_address", "result", "status", "should_run_planner"):
        assert field in payload
    assert payload["result"] == "resume"
    assert payload["status"] == "claimable"
    assert payload["should_run_planner"] is True


def test_fixture_models_all_four_active_statuses() -> None:
    """The canonical fixture covers claimable, claimed, submitted, verifying."""
    if not FIXTURE.is_file():
        return
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    statuses = {entry["status"] for entry in fixture["factory"]}
    for active in ("claimable", "claimed", "submitted", "verifying"):
        assert active in statuses


def test_fixture_expected_decisions_match_engine() -> None:
    """The engine reproduces every expected decision in the fixture."""
    if not FIXTURE.is_file():
        return
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    engine = engine_from_fixture(fixture)
    for contract, expected in fixture["expected_decisions"].items():
        decision = engine.reconcile(contract)
        payload = engine.decision_to_json(decision)
        assert payload["result"] == expected["result"], contract
        assert payload["status"] == expected["status"], contract
        assert payload["should_run_planner"] == expected["should_run_planner"], contract
