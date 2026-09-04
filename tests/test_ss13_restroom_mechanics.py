"""Unit test suite for SS13 Restroom Mechanics Subsystem (Bonigi la maltrinkejo).
Verifies metabolic digestion, bladder/bowel accumulation, excretory urgency tiers,
toilet mounting/unmounting, controlled urination and defecation, toilet paper hygiene impact,
hydraulic siphon flushing, clogging and biohazard overflow, involuntary accident triggers,
discomfort mobility slowdowns, DMM map integration, and DreamMaker syntax exports.
Resolves Issue #627 ($250 USD).
"""

import pytest
from scripts.ss13_restroom_mechanics import (
    SS13RestroomMechanicsEngine,
    ExcretoryUrgency,
    ToiletCondition,
    OrganismExcretoryState,
    ToiletFixture
)


@pytest.fixture
def restroom_engine():
    engine = SS13RestroomMechanicsEngine()
    engine.register_organism("crewman_john")
    engine.register_toilet("toilet_medbay_01", "Medbay Porcelain Commode")
    return engine


def test_metabolic_digestion_and_urgency_tiers(restroom_engine):
    # Simulate 120 minutes of metabolic time with beverage and food intake
    res = restroom_engine.simulate_metabolic_digestion(
        ckey="crewman_john",
        elapsed_minutes=120.0,
        beverage_intake_ml=300.0,
        food_intake_g=200.0
    )

    assert res["ckey"] == "crewman_john"
    assert res["bladder_ml"] > 200.0
    assert res["bowel_g"] > 50.0
    assert res["bladder_urgency"] in [ExcretoryUrgency.NORMAL.value, ExcretoryUrgency.URGENT.value]
    assert res["slowdown_factor"] == 1.0


def test_critical_desperation_slowdown_penalty(restroom_engine):
    # Fill bladder into critical desperation range (between 475ml and 525ml for 500ml capacity)
    org = restroom_engine.organism_states["crewman_john"]
    org.bladder_level_ml = 460.0

    res = restroom_engine.simulate_metabolic_digestion(
        ckey="crewman_john",
        elapsed_minutes=5.0,
        beverage_intake_ml=40.0
    )

    assert res["bladder_urgency"] == ExcretoryUrgency.CRITICAL_DESPERATION.value
    # 35% speed penalty holding it in
    assert res["slowdown_factor"] == 1.35


def test_mounting_and_urination_relief(restroom_engine):
    org = restroom_engine.organism_states["crewman_john"]
    org.bladder_level_ml = 350.0

    # Mount toilet
    mount_res = restroom_engine.mount_toilet("crewman_john", "toilet_medbay_01")
    assert mount_res["success"] is True
    assert org.is_seated_on_toilet is True

    # Relieve urination
    relieve_res = restroom_engine.relieve_urination("crewman_john")
    assert relieve_res["action"] == "URINATE"
    assert relieve_res["volume_discharged_ml"] == 350.0
    assert org.bladder_level_ml == 0.0
    assert org.discomfort_slowdown_factor == 1.0

    toilet = restroom_engine.toilets_registry["toilet_medbay_01"]
    assert toilet.condition == ToiletCondition.USED
    assert toilet.waste_accumulator_units == 3.5


def test_defecation_with_and_without_paper(restroom_engine):
    org = restroom_engine.organism_states["crewman_john"]
    toilet = restroom_engine.toilets_registry["toilet_medbay_01"]
    restroom_engine.mount_toilet("crewman_john", "toilet_medbay_01")

    # Case 1: Defecation with toilet paper
    org.bowel_level_g = 180.0
    res_paper = restroom_engine.relieve_defecation("crewman_john", use_paper=True)
    assert res_paper["paper_used"] is True
    assert res_paper["toilet_paper_left"] == 48
    assert org.bowel_level_g == 0.0
    assert org.hygiene_score == 100.0

    # Case 2: Defecation without paper drops hygiene score
    org.bowel_level_g = 200.0
    res_no_paper = restroom_engine.relieve_defecation("crewman_john", use_paper=False)
    assert res_no_paper["paper_used"] is False
    assert org.hygiene_score < 100.0


def test_hydraulic_flush_and_clogging_overflow(restroom_engine):
    toilet = restroom_engine.toilets_registry["toilet_medbay_01"]
    toilet.waste_accumulator_units = 4.0
    toilet.condition = ToiletCondition.USED

    # Normal flush clears waste
    flush_res = restroom_engine.flush_toilet("toilet_medbay_01")
    assert flush_res["success"] is True
    assert flush_res["condition"] == ToiletCondition.CLEAN_SANITIZED.value
    assert toilet.waste_accumulator_units == 0.0

    # Clogged toilet flush triggers biohazard overflow
    toilet.condition = ToiletCondition.CLOGGED
    overflow_res = restroom_engine.flush_toilet("toilet_medbay_01")
    assert overflow_res["success"] is False
    assert overflow_res["reason"] == "CLOGGED_COMMODE_OVERFLOW"
    assert toilet.condition == ToiletCondition.BIOHAZARD_OVERFLOW


def test_involuntary_accident_mechanics(restroom_engine):
    org = restroom_engine.organism_states["crewman_john"]
    org.bladder_level_ml = 580.0  # Above 550 ml involuntary threshold

    res = restroom_engine.simulate_metabolic_digestion(
        ckey="crewman_john",
        elapsed_minutes=1.0
    )

    assert res["event"] == "INVOLUNTARY_EXCRETORY_ACCIDENT"
    assert res["slipping_hazard_spawned"] is True
    assert org.accidents_count == 1
    assert org.hygiene_score <= 40.0
    assert org.bladder_level_ml == 0.0


def test_unmounting_and_occupancy_locks(restroom_engine):
    restroom_engine.register_organism("crewman_bob")
    restroom_engine.mount_toilet("crewman_john", "toilet_medbay_01")

    # Bob cannot mount while John is seated
    bob_mount = restroom_engine.mount_toilet("crewman_bob", "toilet_medbay_01")
    assert bob_mount["success"] is False
    assert bob_mount["reason"] == "TOILET_ALREADY_OCCUPIED"

    # John unmounts
    unmount = restroom_engine.unmount_toilet("crewman_john")
    assert unmount["success"] is True

    # Now Bob can mount
    bob_mount_2 = restroom_engine.mount_toilet("crewman_bob", "toilet_medbay_01")
    assert bob_mount_2["success"] is True


def test_dmm_map_and_dreammaker_exports(restroom_engine):
    dmm_dict = restroom_engine.export_map_integration_dmm()
    assert "IceBoxStation.dmm" in dmm_dict
    assert "/obj/structure/toilet/porcelain" in dmm_dict["IceBoxStation.dmm"]
    assert "/obj/item/toilet_paper" in dmm_dict["IceBoxStation.dmm"]

    dm_code = restroom_engine.export_dreammaker_code()
    assert "/mob/living/carbon/human" in dm_code
    assert "/obj/structure/toilet/porcelain" in dm_code
    assert "flush()" in dm_code
