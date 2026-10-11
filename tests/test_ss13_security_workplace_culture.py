"""Unit tests for SS13 Security Rework: Workplace Culture Center & De-escalation Reform Engine.
Resolves Issue #590: [paid PR opire bounty $250 TG USD CREDS] [EASY TASK FOR AGENTS] [AGENTIC]
Implement the Security Rework: Workplace Culture Center and The Rest Of It design docs.
Upstream Reference: Iamgoofball/-tg-station#46.
"""

import pytest
from scripts.ss13_security_workplace_culture import (
    SS13SecurityWorkplaceCultureSystem,
    OfficerStressLevel,
    CitationType,
    PositiveCitation,
    OfficerWellnessProfile,
)


@pytest.fixture
def culture_system():
    return SS13SecurityWorkplaceCultureSystem()


def test_officer_registration_and_stress_levels(culture_system):
    profile = culture_system.register_officer("OfficerFriendly", initial_stress=15.0)
    assert profile.ckey == "OfficerFriendly"
    assert culture_system.get_stress_status("OfficerFriendly") == OfficerStressLevel.ZEN_PEACEFUL

    # Elevated stress testing
    profile.stress_points = 35.0
    assert culture_system.get_stress_status("OfficerFriendly") == OfficerStressLevel.CALM_ALERT

    profile.stress_points = 60.0
    assert culture_system.get_stress_status("OfficerFriendly") == OfficerStressLevel.ELEVATED_TENSION

    profile.stress_points = 80.0
    assert culture_system.get_stress_status("OfficerFriendly") == OfficerStressLevel.AGITATION_RISK

    profile.stress_points = 95.0
    assert culture_system.get_stress_status("OfficerFriendly") == OfficerStressLevel.BURNOUT_MELTDOWN


def test_deescalation_success_reduces_stress_and_boosts_rating(culture_system):
    culture_system.register_officer("WardenSmith", initial_stress=50.0)
    res = culture_system.record_deescalation_attempt(
        officer_ckey="WardenSmith",
        suspect_ckey="RowdyAssistant",
        dialogue_choice="Offer hot chocolate and calm conversation",
        is_successful=True,
    )

    assert res["status"] == "PEACEFULLY_RESOLVED"
    profile = culture_system.officer_profiles["WardenSmith"]
    assert profile.stress_points == 35.0  # 50 - 15
    assert profile.deescalation_rating == 87.5  # 85 + 2.5
    assert len(culture_system.deescalation_logs) == 1


def test_deescalation_failure_increases_stress(culture_system):
    culture_system.register_officer("RookieJones", initial_stress=30.0)
    res = culture_system.record_deescalation_attempt(
        officer_ckey="RookieJones",
        suspect_ckey="AggressiveMime",
        dialogue_choice="Demand immediate quiet in common hallway",
        is_successful=False,
    )

    assert res["status"] == "ESCALATED_STANDOFF"
    profile = culture_system.officer_profiles["RookieJones"]
    assert profile.stress_points == 40.0  # 30 + 10


def test_wellness_tea_session_clears_burnout(culture_system):
    culture_system.register_officer("StressedDetective", initial_stress=85.0)
    profile = culture_system.officer_profiles["StressedDetective"]
    profile.mandatory_retraining = True

    # Partake in soothing tea
    res = culture_system.partake_wellness_tea_session("StressedDetective", blend="chamomile_mint")
    assert res["status"] == "RELAXED_AND_REFLECTIVE"
    assert profile.stress_points == 55.0  # 85 - 30
    assert profile.wellness_tea_cups_consumed == 1
    assert profile.mandatory_retraining is False


def test_positive_citation_award_and_registry(culture_system):
    culture_system.register_officer("SergeantPeace", initial_stress=25.0)
    citation = culture_system.award_positive_citation(
        officer_ckey="SergeantPeace",
        recipient_ckey="CooperativeClown",
        citation_type=CitationType.HARMLESS_HONKING_COEXISTENCE,
        notes="Safely amused passengers without slipping anyone into hazardous airlocks.",
    )

    assert citation.recipient_ckey == "CooperativeClown"
    assert citation.citation_type == CitationType.HARMLESS_HONKING_COEXISTENCE
    assert citation.stipend_bonus_credits == 75
    assert len(culture_system.citations_registry) == 1

    profile = culture_system.officer_profiles["SergeantPeace"]
    assert profile.stress_points == 20.0  # 25 - 5
    assert len(profile.citations_awarded) == 1


def test_excessive_force_reports_trigger_mandatory_retraining(culture_system):
    culture_system.register_officer("BrutalEnforcer", initial_stress=50.0)
    res = culture_system.report_excessive_force(
        officer_ckey="BrutalEnforcer",
        reason="Discharged heavy stun baton on unarmed civilian over parking ticket",
    )

    assert res["mandatory_retraining"] is True
    assert res["disciplinary_action"] == "REFERRED_TO_WORKPLACE_CULTURE_CENTER"
    profile = culture_system.officer_profiles["BrutalEnforcer"]
    assert profile.excessive_force_incidents == 1
    assert profile.stress_points == 75.0
    assert profile.deescalation_rating == 70.0  # 85 - 15


def test_map_integration_dmm_export(culture_system):
    maps = culture_system.export_map_integration_dmm()
    assert "IceBoxStation.dmm" in maps
    assert "runtimestation.dmm" in maps
    assert "tramstation.dmm" in maps
    assert "/obj/machinery/culture_center_terminal" in maps["IceBoxStation.dmm"]


def test_dreammaker_syntax_export(culture_system):
    dm = culture_system.export_dreammaker_code()
    assert "/datum/subsystem/workplace_culture" in dm
    assert "/obj/machinery/culture_center_terminal" in dm
    assert "/obj/structure/chair/wellness_lounger" in dm
    assert "/obj/item/citation/positive_reinforcement" in dm
    assert "evaluate_deescalation" in dm
