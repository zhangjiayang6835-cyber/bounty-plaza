"""Unit tests for SS13 Domestic Operations: The Great Agile Marital Refactor Engine.
Resolves Issue #600: [BOUNTY][$500 NT SpaceBucks™] Fix my failing marriage.
"""

import pytest
from scripts.ss13_agile_marriage_refactor import (
    UserStoryPriority,
    UserStoryStatus,
    MaritalHealthStatus,
    MaritalUserStory,
    DailyStandupReport,
    EmotionalBugLog,
    AgileMarriageCounselingEngine,
)


def test_initial_marital_backlog_and_stakeholders():
    engine = AgileMarriageCounselingEngine()
    assert len(engine.active_backlog) >= 5
    assert "US-101" in engine.active_backlog
    assert "US-202" in engine.active_backlog
    assert engine.judgmental_cat_approval_pct == 75.0
    assert engine.current_sprint_number == 1
    assert engine.sprint_duration_days == 14


def test_daily_standup_three_questions():
    engine = AgileMarriageCounselingEngine()
    report = engine.submit_daily_standup(
        partner_name="Partner A",
        yesterday_contribution="Made breakfast and took out diaper recycling",
        today_commitments="Empty dishwasher and defuse toddler clothing negotiation",
        blockers="Toddler refusing pants"
    )
    assert report.partner_name == "Partner A"
    assert report.blockers == "Toddler refusing pants"
    assert len(engine.daily_standup_history) == 1
    assert engine.judgmental_cat_approval_pct > 75.0


def test_sprint_planning_capacity_limits():
    engine = AgileMarriageCounselingEngine()
    # Plan sprint with US-101 (3 SP), US-202 (5 SP), and US-303 (2 SP) = 10 SP <= 20 SP capacity
    plan_res = engine.plan_sprint(["US-101", "US-202", "US-303"])
    assert plan_res["status"] == "SPRINT_PLANNED"
    assert plan_res["committed_story_points"] == 10
    assert len(engine.active_sprint_stories) == 3
    assert engine.active_sprint_stories["US-101"].status == UserStoryStatus.IN_SPRINT


def test_complete_story_and_dishwasher_streak():
    engine = AgileMarriageCounselingEngine()
    engine.plan_sprint(["US-101", "US-202"])

    res = engine.complete_story("US-101")
    assert res["status"] == "STORY_DONE"
    assert res["story_id"] == "US-101"
    assert engine.dishwasher_empty_streak_days == 1
    assert engine.active_sprint_stories["US-101"].status == UserStoryStatus.DONE

    # Attempting to complete non-sprint story raises KeyError
    with pytest.raises(KeyError, match="not in current active sprint"):
        engine.complete_story("US-505")


def test_emotional_bug_logging_and_resolution():
    engine = AgileMarriageCounselingEngine()
    bug = engine.log_emotional_bug(
        bug_id="BUG-001",
        severity="major",
        trigger_event="Tone of voice during dinner prep",
        action_plan="Practice 5-second breath pause before answering"
    )
    assert bug.bug_id == "BUG-001"
    assert bug.is_resolved is False

    # Resolve bug
    resolve_res = engine.resolve_emotional_bug("BUG-001")
    assert resolve_res["status"] == "BUG_RESOLVED"
    assert bug.is_resolved is True


def test_marital_health_evaluation():
    engine = AgileMarriageCounselingEngine()
    # Initial state with no stories completed -> technical debt warning
    init_health = engine.evaluate_marital_health()
    assert init_health["status"] == MaritalHealthStatus.TECHNICAL_DEBT_WARNING.value

    # Plan and complete high points stories
    engine.plan_sprint(["US-101", "US-202", "US-303", "US-404"])
    engine.complete_story("US-101")  # 3 SP
    engine.complete_story("US-202")  # 5 SP
    engine.complete_story("US-303")  # 2 SP -> Total 10 SP
    engine.complete_story("US-404")  # 5 SP -> Total 15 SP

    thriving_health = engine.evaluate_marital_health()
    assert thriving_health["status"] == MaritalHealthStatus.THRIVING_AGILE.value
    assert thriving_health["completed_story_points"] == 15


def test_dreammaker_export():
    engine = AgileMarriageCounselingEngine()
    dm = engine.export_dreammaker_definitions()
    assert "/obj/machinery/computer/agile_marriage_board" in dm
    assert "record_standup" in dm
