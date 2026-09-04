"""Unit tests for Core Rules Policy Engine and Moderation Automation Subsystem.
Resolves Issue #667: [BOUNTY] [$2500] Codify server policy to relieve staff workload part one: core rules.
"""

import pytest
from scripts.core_rules_policy_engine import (
    CoreRulesPolicyEngine,
    RuleViolationSeverity,
    PolicyEvaluationResult,
)


@pytest.fixture
def engine():
    return CoreRulesPolicyEngine()


def test_cr1_proactive_self_reporting(engine):
    """Tests that proactive self-reporting records mitigation credits and relieves staff triage."""
    report = engine.record_self_report(
        ckey="sample_player_1",
        incident_description="Accidentally ruptured plasma pipe in toxins test chamber",
        details={"tile_damage": 12, "crew_injuries": 0},
    )
    assert report["mitigation_credit_granted"] is True
    assert report["staff_action_recommended"] == "INFORMAL_COUNSEL_ONLY"
    assert len(engine.self_reports) == 1


def test_cr1_2_conflict_cessation_pending_ticket(engine):
    """Tests CR 1.2 enforcement: all conflict with accused party must immediately cease once ticket is opened."""
    # Open ticket
    ticket = engine.open_ticket("TKT-10492", reporting_ckey="crew_alice", accused_ckey="crew_bob")
    assert ticket.is_pending is True

    # Hostile/retributive action while ticket pending must be blocked
    eval_hostile = engine.validate_interaction_during_ticket(
        actor_ckey="crew_alice",
        target_ckey="crew_bob",
        is_hostile_or_retributive=True,
    )
    assert eval_hostile.passed is False
    assert eval_hostile.severity == RuleViolationSeverity.CRITICAL_STAFF_ESCALATION
    assert "Rule Violation [CR 1.2]" in eval_hostile.message

    # Neutral/non-hostile interaction is permitted
    eval_neutral = engine.validate_interaction_during_ticket(
        actor_ckey="crew_alice",
        target_ckey="crew_bob",
        is_hostile_or_retributive=False,
    )
    assert eval_neutral.passed is True


def test_cr1_3_tap_out_rule_disengagement(engine):
    """Tests CR 1.3: Invoking the Tap Out Rule immediately blocks targeted interaction from the other party."""
    engine.invoke_tap_out(
        invoking_ckey="crew_carol",
        target_ckey="crew_dave",
        looc_message="Invoking the Tap Out Rule",
    )

    # Dave attempting targeted interaction with Carol must fail
    check = engine.check_tap_out_boundary(actor_ckey="crew_dave", target_ckey="crew_carol")
    assert check.passed is False
    assert check.severity == RuleViolationSeverity.ACTION_REQUIRED
    assert "Rule Violation [CR 1.3]" in check.message

    # Unrelated player interaction passes
    check_other = engine.check_tap_out_boundary(actor_ckey="crew_eve", target_ckey="crew_carol")
    assert check_other.passed is True


def test_cr1_4_leave_real_history_in_the_past(engine):
    """Tests CR 1.4: In-game chat filtering of controversial modern political/historical figures."""
    # Chat with controversial modern political reference
    res_bad = engine.evaluate_chat_message_for_history_rule("Did you hear what Putin said on the radio?")
    assert res_bad.passed is False
    assert res_bad.severity == RuleViolationSeverity.WARNING
    assert "Rule Violation [CR 1.4]" in res_bad.message

    # Futuristic in-lore chat passes
    res_good = engine.evaluate_chat_message_for_history_rule("The Sol Gov fleet has docked at Station 13.")
    assert res_good.passed is True
    assert res_good.severity == RuleViolationSeverity.INFO


def test_dm_policy_definitions_generation(engine):
    """Tests DM policy datum declaration generation for TG-Station."""
    dm_defs = engine.generate_dm_policy_definitions()
    assert "/datum/policy_rule/core" in dm_defs
    assert "CR 1.1" in dm_defs
    assert "CR 1.2" in dm_defs
    assert "CR 1.3" in dm_defs
    assert "CR 1.4" in dm_defs
    assert "The Tap Out Rule" in dm_defs
