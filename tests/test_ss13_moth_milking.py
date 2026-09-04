"""Unit test suite for SS13 Mothpeople Milking & Silk-Lipid Lactation Subsystem.
Verifies fiber feeding and metabolism, antenna brushing/lamp happiness boosts,
lactation volume replenishment over time, gentle/automated/industrial extraction methods,
milk grade evaluation (Grade A Silk Nectar, Grade B Standard, Grade C Stressed),
culinary and textile processing (cheese, butter, organic silk thread), non-moth rejection gates,
DMM map coordinates, and DreamMaker syntax exports.
Resolves Issue #624 ($67.69 USD).
"""

import pytest
from scripts.ss13_moth_milking import (
    SS13MothMilkingEngine,
    SpeciesClassification,
    MilkingMethod,
    MothMilkGrade,
    MothpersonPhysiology,
    MilkerApparatus
)


@pytest.fixture
def moth_engine():
    engine = SS13MothMilkingEngine()
    engine.register_mothperson("jane_moth", initial_milk_ml=60.0, happiness=85.0)
    engine.register_milker_machine("milker_shed_01", "Pastoral Milker Stool")
    return engine


def test_fiber_feeding_and_happiness_multipliers(moth_engine):
    # Feed luxury cashmere/wool
    res_wool = moth_engine.feed_cellulose_fiber("jane_moth", fiber_type="cashmere_scarf", mass_grams=50.0)
    assert res_wool["ckey"] == "jane_moth"
    assert res_wool["added_fiber_units"] == 20.0  # 50 * 0.2 * 2.0
    assert res_wool["happiness"] == 100.0  # 85 + 15 capped at 100

    # Verify total reserve updated
    moth = moth_engine.moth_registry["jane_moth"]
    assert moth.fiber_digested_units == 40.0  # initial 20 + 20


def test_antenna_brushing_and_lamp_basking(moth_engine):
    moth_engine.moth_registry["jane_moth"].happiness_level = 60.0
    res = moth_engine.brush_antennae_and_bask_lamp("jane_moth")
    assert res["happiness_level"] == 80.0
    assert "chitters contentedly" in res["message"]


def test_lactation_replenishment_simulation(moth_engine):
    moth = moth_engine.moth_registry["jane_moth"]
    moth.milk_reservoir_ml = 30.0
    moth.fiber_digested_units = 30.0

    # Simulate 10 minutes (lactation rate 2.5 ml/min = 25 ml potential)
    res = moth_engine.simulate_lactation_replenishment("jane_moth", elapsed_minutes=10.0)
    assert res["milk_reservoir_ml"] == 55.0  # 30 + 25
    assert res["fiber_remaining"] == 30.0 - (25.0 * 0.15)


def test_manual_gentle_milking_grade_a(moth_engine):
    moth = moth_engine.moth_registry["jane_moth"]
    moth.happiness_level = 90.0

    res = moth_engine.milk_mothperson(
        extractor_ckey="botanist_bob",
        moth_ckey="jane_moth",
        method=MilkingMethod.MANUAL_GENTLE_HAND,
        apparatus_id="milker_shed_01"
    )

    assert res["success"] is True
    assert res["volume_extracted_ml"] == 30.0
    assert res["milk_grade"] == MothMilkGrade.GRADE_A_SILK_NECTAR.value
    assert res["bioluminescent_glow"] is True
    assert res["remaining_milk_ml"] == 30.0
    assert res["moth_happiness"] == 95.0

    # Verify apparatus received the milk
    machine = moth_engine.milker_registry["milker_shed_01"]
    assert machine.collected_milk_ml == 30.0
    assert machine.milk_reagent_grade == MothMilkGrade.GRADE_A_SILK_NECTAR


def test_rapid_industrial_milking_stress_and_grade_c(moth_engine):
    moth = moth_engine.moth_registry["jane_moth"]
    moth.milk_reservoir_ml = 80.0
    moth.happiness_level = 40.0

    # Industrial extraction completely empties reservoir but causes severe stress
    res = moth_engine.milk_mothperson(
        extractor_ckey="ruthless_miner",
        moth_ckey="jane_moth",
        method=MilkingMethod.RAPID_INDUSTRIAL_SUCTION
    )

    assert res["success"] is True
    assert res["volume_extracted_ml"] == 80.0
    assert res["remaining_milk_ml"] == 0.0
    assert res["milk_grade"] == MothMilkGrade.GRADE_C_SYNTHETIC_STRESSED.value
    assert res["moth_happiness"] == 15.0  # 40 - 25


def test_non_mothperson_rejection():
    engine = SS13MothMilkingEngine()
    # Register human
    human = MothpersonPhysiology(ckey="captain_steve", species=SpeciesClassification.HUMAN)
    engine.moth_registry["captain_steve"] = human

    res = engine.milk_mothperson(
        extractor_ckey="clown",
        moth_ckey="captain_steve",
        method=MilkingMethod.MANUAL_GENTLE_HAND
    )
    assert res["success"] is False
    assert res["reason"] == "SPECIES_CANNOT_BE_MILKED_NOT_MOTHPERSON"


def test_dairy_product_processing(moth_engine):
    # Cheese conversion
    res_cheese = moth_engine.process_dairy_products(100.0, "cheese")
    assert res_cheese["product"] == "/obj/item/food/cheese/moth_silk_wheel"
    assert res_cheese["units_produced"] == 2.0

    # Butter conversion
    res_butter = moth_engine.process_dairy_products(50.0, "butter")
    assert res_butter["product"] == "/obj/item/food/butter/moth_butter"
    assert res_butter["units_produced"] == 1.0

    # High-tensile silk thread conversion
    res_silk = moth_engine.process_dairy_products(150.0, "silk_thread")
    assert res_silk["product"] == "/obj/item/stack/sheet/cloth/organic_silk"
    assert res_silk["units_produced"] == 5.0


def test_dmm_map_and_dreammaker_exports(moth_engine):
    dmm_dict = moth_engine.export_map_integration_dmm()
    assert "IceBoxStation.dmm" in dmm_dict
    assert "/obj/machinery/moth_milker_stool" in dmm_dict["IceBoxStation.dmm"]
    assert "/obj/item/reagent_containers/food/drinks/bottle/moth_milk" in dmm_dict["IceBoxStation.dmm"]

    dm_code = moth_engine.export_dreammaker_code()
    assert "/datum/reagent/consumable/moth_milk" in dm_code
    assert "/datum/species/moth" in dm_code
    assert "can_be_milked()" in dm_code
    assert "/obj/machinery/moth_milker_stool" in dm_code
