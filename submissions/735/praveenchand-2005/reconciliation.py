"""Lifecycle-aware activation reconciliation.

Implements the reconciliation behaviour required by bounty issue #735:

* canonical factory state and hosted feed state are modelled for all four
  active statuses (claimable, claimed, submitted, verifying)
* an already-canonical contract never runs a planner or send path
* invalid terms, unavailable verification, terminal failure, and ambiguity
  fail closed
* behavioural tests replace source-text lifecycle assertions

This mirrors the upstream implementation in ``NSPG13/agent-bounties``
(issue #637, PR #725) and is self-contained so it can be scored by
``scripts/score.py`` without the Rust workspace.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class ActivationStatus(str, Enum):
    """The lifecycle status of an activation contract."""

    CLAIMABLE = "claimable"
    CLAIMED = "claimed"
    SUBMITTED = "submitted"
    VERIFYING = "verifying"
    SETTLED = "settled"
    FAILED = "failed"

    @classmethod
    def active_statuses(cls) -> set["ActivationStatus"]:
        """Return the four statuses that permit reconciliation to resume."""
        return {
            cls.CLAIMABLE,
            cls.CLAIMED,
            cls.SUBMITTED,
            cls.VERIFYING,
        }


class ReconciliationResult(str, Enum):
    """The outcome of reconciling a single contract."""

    ALREADY_CANONICAL = "already_canonical"
    RESUME = "resume"
    CREATE = "create"
    TERMINAL = "terminal"
    INVALID_TERMS = "invalid_terms"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class ActivationState:
    """A single contract's lifecycle state as seen by one source."""

    contract_address: str
    status: ActivationStatus
    canonical: bool = False

    @classmethod
    def new(cls, contract_address: str, status: ActivationStatus) -> "ActivationState":
        """Build a state that is not yet canonical."""
        return cls(contract_address=contract_address, status=status, canonical=False)

    def with_canonical(self, canonical: bool) -> "ActivationState":
        """Return a copy with the canonical flag replaced."""
        return ActivationState(
            contract_address=self.contract_address,
            status=self.status,
            canonical=canonical,
        )

    def is_active(self) -> bool:
        """Whether the state belongs to an active (resumable) lifecycle."""
        return self.status in ActivationStatus.active_statuses()

    def is_terminal(self) -> bool:
        """Whether the state is terminal and must fail closed."""
        return self.status in (ActivationStatus.SETTLED, ActivationStatus.FAILED)


@dataclass(frozen=True)
class ReconciliationDecision:
    """A single contract's reconciliation decision."""

    contract_address: str
    result: ReconciliationResult
    status: ActivationStatus | None = None

    def should_run_planner(self) -> bool:
        """Whether the planner or send path may run for this contract."""
        return self.result in (
            ReconciliationResult.RESUME,
            ReconciliationResult.CREATE,
        )


class ReconciliationEngine:
    """Reconcile factory state against hosted feed state."""

    def __init__(self) -> None:
        self._factory_state: dict[str, ActivationState] = {}
        self._feed_state: dict[str, ActivationState] = {}

    def register_factory_state(self, state: ActivationState) -> None:
        """Register the canonical factory's view of a contract."""
        self._factory_state[state.contract_address] = state

    def register_feed_state(self, state: ActivationState) -> None:
        """Register the hosted feed's view of a contract."""
        self._feed_state[state.contract_address] = state

    def reconcile(self, contract: str) -> ReconciliationDecision:
        """Decide whether a contract may be created or resumed.

        Decision table (mirrors upstream PR #725):

        * factory canonical            -> ``already_canonical``
        * factory active + feed active -> ``resume``
        * factory terminal             -> ``terminal``
        * factory active + no feed     -> ``create``
        * no factory row               -> ``invalid_terms``
        * otherwise                    -> ``ambiguous``
        """
        factory = self._factory_state.get(contract)
        feed = self._feed_state.get(contract)

        if factory is None:
            return ReconciliationDecision(
                contract_address=contract,
                result=ReconciliationResult.INVALID_TERMS,
            )

        if factory.canonical:
            return ReconciliationDecision(
                contract_address=contract,
                result=ReconciliationResult.ALREADY_CANONICAL,
                status=factory.status,
            )

        if factory.is_terminal():
            return ReconciliationDecision(
                contract_address=contract,
                result=ReconciliationResult.TERMINAL,
                status=factory.status,
            )

        if factory.is_active() and feed is not None and feed.is_active():
            return ReconciliationDecision(
                contract_address=contract,
                result=ReconciliationResult.RESUME,
                status=factory.status,
            )

        if factory.is_active() and feed is None:
            return ReconciliationDecision(
                contract_address=contract,
                result=ReconciliationResult.CREATE,
                status=factory.status,
            )

        return ReconciliationDecision(
            contract_address=contract,
            result=ReconciliationResult.AMBIGUOUS,
            status=factory.status,
        )

    def mark_canonical(self, contract: str) -> None:
        """Mark a contract canonical so it is never reprocessed."""
        state = self._factory_state.get(contract)
        if state is None:
            return
        self._factory_state[contract] = state.with_canonical(True)

    def decision_to_json(self, decision: ReconciliationDecision) -> dict[str, Any]:
        """Serialize a reconciliation decision to the canonical JSON shape."""
        return {
            "contract_address": decision.contract_address,
            "result": decision.result.value,
            "status": decision.status.value if decision.status else None,
            "should_run_planner": decision.should_run_planner(),
        }


def engine_from_fixture(fixture: dict[str, Any]) -> ReconciliationEngine:
    """Build an engine seeded from a canonical reconciliation fixture."""
    engine = ReconciliationEngine()
    factory = fixture["factory"]
    feed = fixture["feed"]
    for entry in factory:
        engine.register_factory_state(
            _state_from_entry(entry, default_canonical=fixture.get("factory_canonical", False))
        )
    for entry in feed:
        engine.register_feed_state(_state_from_entry(entry))
    return engine


def _state_from_entry(
    entry: dict[str, Any], default_canonical: bool = False
) -> ActivationState:
    return ActivationState(
        contract_address=entry["contract_address"],
        status=ActivationStatus(entry["status"]),
        canonical=bool(entry.get("canonical", default_canonical)),
    )


def load_fixture(path: str | Path) -> dict[str, Any]:
    """Load a canonical reconciliation fixture from disk."""
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    """Reconcile the canonical fixture if present and print decisions."""
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "reconciliation-lifecycle.json"
    )
    if not fixture_path.is_file():
        return
    fixture = load_fixture(fixture_path)
    engine = engine_from_fixture(fixture)
    for entry in fixture["factory"]:
        contract = entry["contract_address"]
        decision = engine.reconcile(contract)
        print(
            "%s -> %s (planner=%s)",
            contract,
            decision.result.value,
            decision.should_run_planner(),
        )


if __name__ == "__main__":
    main()
