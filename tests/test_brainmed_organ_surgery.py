"""Unit tests for Brainmed Organ & Advanced Surgery Simulation Engine.
Resolves Issue #641: [BOUNTY] [AGENTIC AI] [$1,000] [MYTHOS/FABLE CLASS MODEL RECOMMENDED] Port Brainmed.
Upstream Reference: Iamgoofball/-tg-station#158, DaedalusDock/daedalusdock, and Baystation 12.
"""

import pytest
from scripts.brainmed_organ_surgery import (
    BrainmedEngine,
    PatientAnatomy,
    Organ,
    VitalityState,
    SurgeryStage,
)


@pytest.fixture
def engine():
    return BrainmedEngine()


@pytest.fixture
def patient(engine):
    return engine.create_human_anatomy(patient_id="PAT-001", name="Urist McDoctor")


def test_anatomy_initialization_all_organs(patient):
    assert len(patient.organs) == 6
    for organ_name in ["brain", "heart", "lungs", "liver", "kidneys", "eyes"]:
        assert organ_name in patient.organs
        org = patient.organs[organ_name]
        assert org.is_implanted is True
        assert org.current_health == 100.0
        assert org.is_failing is False


def test_baseline_life_tick_conscious_and_stable(engine, patient):
    tick_res = engine.process_life_tick(patient)
    assert tick_res["vital_state"] == VitalityState.CONSCIOUS.value
    assert tick_res["pulse_bpm"] > 70.0
    assert tick_res["blood_oxygen_pct"] >= 98.0
    assert tick_res["brain_damage"] == 0.0


def test_surgical_workflow_and_heart_removal_causes_cardiac_arrest(engine, patient):
    # Progress through valid surgical steps:
    # 0 -> Incision (scalpel)
    s1 = engine.advance_surgery_step(patient, "scalpel")
    assert s1["current_stage"] == "INCISION_MADE"

    # 1 -> Retractor
    s2 = engine.advance_surgery_step(patient, "retractor")
    assert s2["current_stage"] == "RETRACTED"

    # 2 -> Hemostat
    s3 = engine.advance_surgery_step(patient, "hemostat")
    assert s3["current_stage"] == "HEMOSTAT_CLAMPED"

    # 3 -> Saw (expose cavity)
    s4 = engine.advance_surgery_step(patient, "saw")
    assert s4["current_stage"] == "ORGAN_EXPOSED"

    # Remove the heart
    extracted_heart = engine.surgical_remove_organ(patient, "heart")
    assert extracted_heart.name == "Heart"
    assert extracted_heart.is_implanted is False
    assert patient.pulse_bpm == 0.0

    # Advance tick: patient is now in cardiac arrest and accumulates hypoxia / brain damage
    tick1 = engine.process_life_tick(patient)
    assert tick1["vital_state"] == VitalityState.CARDIAC_ARREST.value
    assert tick1["pulse_bpm"] == 0.0
    assert patient.brain_damage > 0.0


def test_brainmed_paradigm_hypoxia_leads_to_brain_death(engine, patient):
    # Remove lungs to cut off oxygenation while heart beats
    patient.surgery_stage = SurgeryStage.ORGAN_EXPOSED
    engine.surgical_remove_organ(patient, "lungs")

    # Run consecutive ticks simulating progressive cerebral ischemic damage
    for _ in range(40):
        engine.process_life_tick(patient)

    # In Brainmed, severe oxygen depletion causes brain death
    assert patient.brain_damage >= 100.0
    assert engine._determine_vitality_state(patient) == VitalityState.BRAIN_DEAD


def test_daedalus_pharmacology_mannitol_and_epinephrine(engine, patient):
    # Inflict initial brain damage
    patient.brain_damage = 30.0
    patient.pulse_bpm = 0.0

    # Administer Mannitol (neuro-regenerator) & Epinephrine
    engine.administer_chemical(patient, "mannitol", units=10.0)
    engine.administer_chemical(patient, "epinephrine", units=5.0)

    initial_bd = patient.brain_damage
    engine.process_life_tick(patient)

    # Mannitol should heal brain damage
    assert patient.brain_damage < initial_bd


def test_health_analyzer_scanner_telemetry(engine, patient):
    scan = engine.scan_with_health_analyzer(patient)
    assert "HEALTH ANALYZER - PATIENT: URIST MCDOCTOR" in scan["scanner_display"]
    assert scan["clinical_status"] == VitalityState.CONSCIOUS.value
    assert "pulse" in scan["vitals"]
    assert "oxygen_saturation" in scan["vitals"]
    assert "brain_health" in scan["vitals"]
    assert "Heart" in scan["organs"]
    assert scan["organs"]["Heart"]["status"] == "IMPLANTED"


def test_dreammaker_export_syntax(engine):
    dm = engine.export_dreammaker_code()
    assert "/obj/item/organ" in dm
    assert "/obj/item/organ/heart" in dm
    assert "/obj/item/organ/brain" in dm
    assert "handle_hypoxia" in dm
