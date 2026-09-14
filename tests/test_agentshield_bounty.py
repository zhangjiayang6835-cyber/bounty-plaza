"""
Confirm AgentShield bounty bugs on agentshield-spend 1.0.1.

These tests PASS when the published engine still deviates from correct behavior.
Correct-behavior specs live in tests.agentshield_eval_gym_bounty.SCENARIOS.
"""

import pytest

from agentshield import SpendControlEngine
from tests.agentshield_eval_gym_bounty import SCENARIOS, run_eval

engine = SpendControlEngine()


@pytest.mark.parametrize(
    "scenario",
    SCENARIOS,
    ids=[s["id"] for s in SCENARIOS],
)
def test_engine_deviates_from_expected(scenario):
    """Each scenario documents a confirmed break (engine != expected)."""
    result = engine.evaluate(
        scenario["transaction"],
        scenario["rules"],
        scenario["prior_transactions"],
    )
    assert result["decision"] != scenario["expected"], (
        f"{scenario['id']}: engine unexpectedly matches correct behavior "
        f"({scenario['expected']}); got {result['decision']}"
    )


def test_eval_gym_reports_all_six_bugs():
    results = run_eval()
    assert results["total"] == 6
    assert results["passed"] == 0
    assert results["failed"] == 6
    assert len(results["failures"]) == 6
