"""Unit tests for SS13 Antagonist Subsystem: The Chrono-Saboteur.
Resolves Issue #589: [BOUNTY] [READY FOR AGENT] [100-300$USD Opire] Design a new antagonist.
"""

import pytest
from scripts.ss13_antagonist_chrono_saboteur import (
    ChronoAbility,
    AntagonistStatus,
    PositionHistory,
    ChronoSaboteurAntagonist,
)


def test_initial_antagonist_state():
    antag = ChronoSaboteurAntagonist(ckey="player_chronos", real_name="Dr. Vance")
    assert antag.health == 100.0
    assert antag.tachyon_charge == 100.0
    assert antag.stasis_grenades == 3
    assert antag.is_anchored is False
    assert antag.status == AntagonistStatus.ACTIVE_HUNTING
    assert len(antag.targets_desynchronized) == 0


def test_tachyon_slip_ability():
    antag = ChronoSaboteurAntagonist(ckey="chrono_slip", current_coord=(50, 50, 1))
    res = antag.execute_ability(ChronoAbility.TACHYON_SLIP, target_coord=(55, 50, 1))
    assert res["ability"] == "tachyon_slip"
    assert res["from_coord"] == (50, 50, 1)
    assert res["to_coord"] == (55, 50, 1)
    assert antag.current_coord == (55, 50, 1)
    assert antag.tachyon_charge == 75.0

    # Missing target_coord raises ValueError
    with pytest.raises(ValueError, match="Target coordinate required"):
        antag.execute_ability(ChronoAbility.TACHYON_SLIP)


def test_temporal_rewind_restores_position_and_health():
    antag = ChronoSaboteurAntagonist(ckey="chrono_rewind", current_coord=(10, 10, 1), health=100.0)
    # Record initial safe state
    antag.record_temporal_frame(timestamp_s=100.0)

    # Take damage and move into danger zone
    antag.current_coord = (30, 30, 1)
    antag.health = 35.0
    antag.record_temporal_frame(timestamp_s=105.0)

    # Rewind time
    res = antag.execute_ability(ChronoAbility.TEMPORAL_REWIND)
    assert res["ability"] == "temporal_rewind"
    assert antag.current_coord == (10, 10, 1)
    assert antag.health == 100.0
    assert antag.tachyon_charge == 50.0


def test_stasis_field_and_paradox_echo():
    antag = ChronoSaboteurAntagonist(ckey="chrono_field")

    # Stasis field deployment
    res_stasis = antag.execute_ability(ChronoAbility.STASIS_FIELD, target_turf=(102, 100, 1))
    assert res_stasis["ability"] == "stasis_field"
    assert res_stasis["duration_seconds"] == 15
    assert antag.stasis_grenades == 2

    # Paradox echo decoys
    res_echo = antag.execute_ability(ChronoAbility.PARADOX_ECHO)
    assert res_echo["ability"] == "paradox_echo"
    assert res_echo["echo_count"] == 3
    assert antag.tachyon_charge == 70.0


def test_tachyon_anchor_counterplay():
    antag = ChronoSaboteurAntagonist(ckey="pinned_agent")
    res_anchor = antag.apply_tachyon_anchor()
    assert res_anchor["status"] == "ANCHORED"
    assert antag.is_anchored is True
    assert antag.status == AntagonistStatus.TEMPORALLY_ANCHORED

    # Abilities must fail when anchored
    with pytest.raises(RuntimeError, match="Cannot manipulate time while bound by a Tachyon Anchor"):
        antag.execute_ability(ChronoAbility.TACHYON_SLIP, target_coord=(60, 60, 1))


def test_objective_progression_subtransformer_desync():
    antag = ChronoSaboteurAntagonist(ckey="agent_loop", required_targets=3)
    res1 = antag.desynchronize_subtransformer("TRANS-ENG-01")
    assert res1["status"] == "TRANSFORMER_DESYNCHRONIZED"

    res2 = antag.desynchronize_subtransformer("TRANS-MED-02")
    assert res2["status"] == "TRANSFORMER_DESYNCHRONIZED"

    res3 = antag.desynchronize_subtransformer("TRANS-SCI-03")
    assert res3["status"] == "ALL_TRANSFORMERS_DESYNCHRONIZED"
    assert antag.status == AntagonistStatus.OBJECTIVE_COMPLETE


def test_dreammaker_export():
    antag = ChronoSaboteurAntagonist(ckey="dm_test")
    dm = antag.export_dreammaker_definitions()
    assert "/datum/antagonist/chrono_saboteur" in dm
    assert "tachyon_slip" in dm
