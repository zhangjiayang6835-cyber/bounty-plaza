"""Unit tests for SS13 Dentist Job, Dental Surgery Suite, and Species Teeth Organ Architecture.
Resolves Issue #588: [paid PR Opire bounty] [HIGH PRIORITY] [$50] Add the Dentist job with teeth organs.
Upstream Reference: Iamgoofball/-tg-station#49.
"""

import pytest
from scripts.ss13_dentist_teeth_system import (
    SS13DentistSystem,
    SpeciesTeethType,
    DentalCondition,
    Tooth,
    TeethOrgan,
)


@pytest.fixture
def dentist_sys():
    return SS13DentistSystem()


def test_species_teeth_anatomy_initialization(dentist_sys):
    human_mouth = dentist_sys.create_teeth_organ_for_species(SpeciesTeethType.HUMAN_STANDARD)
    assert human_mouth.total_teeth == 32
    assert human_mouth.bite_damage == 5.0
    assert len(human_mouth.teeth_list) == 32

    lizard_mouth = dentist_sys.create_teeth_organ_for_species(SpeciesTeethType.LIZARD_SERRATED)
    assert lizard_mouth.total_teeth == 40
    assert lizard_mouth.bite_damage == 12.0
    assert lizard_mouth.bite_toxin == 2.0

    moth_mouth = dentist_sys.create_teeth_organ_for_species(SpeciesTeethType.MOTH_CHITIN_GRINDERS)
    assert moth_mouth.total_teeth == 16
    assert moth_mouth.bite_damage == 3.0

    plasma_mouth = dentist_sys.create_teeth_organ_for_species(SpeciesTeethType.PLASMAMAN_CERAMIC)
    assert plasma_mouth.total_teeth == 32
    assert plasma_mouth.bite_damage == 8.0

    ethereal_mouth = dentist_sys.create_teeth_organ_for_species(SpeciesTeethType.ETHEREAL_CRYSTALLINE)
    assert ethereal_mouth.total_teeth == 28
    assert ethereal_mouth.bite_damage == 6.0


def test_nitrous_oxide_anesthesia_administration(dentist_sys):
    dentist_sys.register_patient("TerrifiedClown", SpeciesTeethType.HUMAN_STANDARD)
    res = dentist_sys.administer_nitrous_oxide_anesthesia("TerrifiedClown", concentration=0.85)

    assert res["status"] == "SEDATED_EUPHORIC"
    assert res["anesthesia_level"] == 0.85
    assert dentist_sys.patient_mouths["TerrifiedClown"].anesthesia_level == 0.85


def test_cavity_filling_restoration(dentist_sys):
    dentist_sys.register_patient("SugarLover", SpeciesTeethType.HUMAN_STANDARD)
    mouth = dentist_sys.patient_mouths["SugarLover"]
    # Induce cavity on molar #1
    molar = mouth.teeth_list[0]
    molar.condition = DentalCondition.CAVITY_DEEP
    molar.cavity_depth = 5.5

    # Perform filling under anesthesia
    dentist_sys.administer_nitrous_oxide_anesthesia("SugarLover", 0.9)
    res = dentist_sys.perform_cavity_filling("SugarLover", tooth_id=1, material="composite_resin")

    assert res["success"] is True
    assert res["pain_felt"] == 0.0
    assert molar.condition == DentalCondition.HEALTHY
    assert molar.cavity_depth == 0.0


def test_tooth_extraction_mechanics(dentist_sys):
    dentist_sys.register_patient("FightVictim", SpeciesTeethType.HUMAN_STANDARD)
    # Extract tooth #8 without anesthesia -> high pain
    res1 = dentist_sys.extract_tooth("FightVictim", tooth_id=8)
    assert res1["success"] is True
    assert res1["patient_pain"] == 75.0
    assert res1["remaining_teeth"] == 31
    assert len(dentist_sys.extracted_teeth_inventory) == 1

    # Extracting same tooth again fails
    res2 = dentist_sys.extract_tooth("FightVictim", tooth_id=8)
    assert res2["success"] is False
    assert "already extracted" in res2["error"]


def test_gold_crown_installation(dentist_sys):
    dentist_sys.register_patient("StationPimp", SpeciesTeethType.HUMAN_STANDARD)
    res = dentist_sys.install_gold_crown("StationPimp", tooth_id=9)
    assert res["success"] is True
    assert res["status"] == "CROWNED_IN_SOLID_GOLD"

    tooth9 = next(t for t in dentist_sys.patient_mouths["StationPimp"].teeth_list if t.tooth_id == 9)
    assert tooth9.is_gold_crowned is True
    assert tooth9.condition == DentalCondition.GOLD_CROWN
    assert tooth9.durability == 150.0


def test_map_integration_dmm_export(dentist_sys):
    dmm_maps = dentist_sys.export_map_integration_dmm()
    assert "IceBoxStation.dmm" in dmm_maps
    assert "runtimestation.dmm" in dmm_maps
    assert "tramstation.dmm" in dmm_maps
    assert "/obj/structure/chair/dentist" in dmm_maps["IceBoxStation.dmm"]


def test_dreammaker_syntax_export(dentist_sys):
    dm = dentist_sys.export_dreammaker_code()
    assert "/datum/job/dentist" in dm
    assert "/obj/item/organ/teeth" in dm
    assert "/obj/item/organ/teeth/lizard" in dm
    assert "/obj/item/organ/teeth/moth" in dm
    assert "/obj/item/organ/teeth/plasmaman" in dm
    assert "/obj/item/organ/teeth/ethereal" in dm
    assert "/obj/structure/chair/dentist" in dm
