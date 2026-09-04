"""Unit tests for SS13 Ratvar Clockwork Power Engine subsystem.
Resolves Issue #606: [BOUNTY] [OPEN] [HIGH PRIORITY] [READY FOR AGENT] [$150 USD REWARD] Add the Ratvar Engine.
"""

import pytest
from scripts.ss13_ratvar_engine import (
    RatvarEngineCore,
    EngineContainmentStatus,
    CultFaction
)


def test_initial_engine_state():
    engine = RatvarEngineCore()
    assert engine.integrity_pct == 45.0
    assert engine.angular_velocity_rpm == 12000.0
    assert engine.is_contained is True
    assert engine.is_rampaging is False
    assert engine.bronze_hopper_kg == 50.0


def test_bronze_feed_validation():
    engine = RatvarEngineCore()
    res = engine.feed_bronze(25.0)
    assert res["status"] == "BRONZE_DEPOSITED"
    assert engine.bronze_hopper_kg == 75.0

    with pytest.raises(ValueError, match="Bronze feed amount must be positive"):
        engine.feed_bronze(-10.0)


def test_optimal_power_generation():
    engine = RatvarEngineCore(integrity_pct=50.0, bronze_hopper_kg=40.0)
    result = engine.process_tick(delta_s=2.0)
    assert result["status"] == EngineContainmentStatus.OPTIMAL_GENERATING.value
    assert result["power_output_mw"] > 0.0
    assert result["rpm"] > 12000.0
    assert engine.is_contained is True


def test_underfed_starvation_power_drop():
    engine = RatvarEngineCore(integrity_pct=10.0, bronze_hopper_kg=0.0)
    result = engine.process_tick(delta_s=2.0)
    assert result["status"] == EngineContainmentStatus.UNDERFED_STARVING.value
    assert result["power_output_mw"] == 0.0
    assert result["rpm"] < 12000.0


def test_overfed_containment_breach_rampage():
    # Overfed with low chain integrity leading to breach
    engine = RatvarEngineCore(integrity_pct=95.0, stasis_chain_integrity=5.0, bronze_hopper_kg=50.0)
    result = engine.process_tick(delta_s=2.0)
    assert result["status"] == EngineContainmentStatus.BREACHED_RAMPAGE.value
    assert engine.is_rampaging is True
    assert engine.is_contained is False
    assert result["damage_radius_tiles"] == 15


def test_cult_sabotage_and_ascension():
    engine = RatvarEngineCore(integrity_pct=30.0)

    # Clockwork cult surges bronze into hopper to liberate Ratvar
    res_clockwork = engine.evaluate_cult_sabotage_or_ascension(
        CultFaction.CLOCKWORK_RATVAR, "overfeed_bronze_pylon"
    )
    assert res_clockwork["objective_progress"] == "LIBERATION_ACCELERATED"
    assert engine.bronze_hopper_kg >= 130.0

    # Blood cult jams conveyors to cause starvation
    res_blood = engine.evaluate_cult_sabotage_or_ascension(
        CultFaction.BLOOD_NARSIE, "corrupt_conveyor_belts"
    )
    assert res_blood["objective_progress"] == "MALFUNCTION_INFLICTED"
    assert engine.conveyor_active is False


def test_dmm_and_dreammaker_export():
    engine = RatvarEngineCore()
    dmm_dict = engine.export_map_integration_dmm()
    assert "IceBoxStation.dmm" in dmm_dict
    assert "runtimestation.dmm" in dmm_dict
    assert "/obj/machinery/power/ratvar_core" in dmm_dict["IceBoxStation.dmm"]

    dm_code = engine.export_dreammaker_code()
    assert "/obj/machinery/power/ratvar_core" in dm_code
    assert "proc/break_containment()" in dm_code
