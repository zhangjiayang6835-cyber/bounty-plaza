"""Unit tests for SS13 Healthcare & Medical Pathology Subsystem: Removal of Cloning (Issue #625).
Verifies permanent deprecation of cloning pods and enhanced surgical/defibrillator revival.
"""

import pytest
from scripts.ss13_remove_cloning import (
    PostCloningMedicalCareSystem,
    MedicalPolicyMode,
    PatientClinicalState,
    PatientRecord,
    OrganHealth,
)


def test_cloning_pod_strictly_rejected():
    system = PostCloningMedicalCareSystem()
    assert system.policy_mode == MedicalPolicyMode.CLONING_DEPRECATED_REMOVED
    assert system.cloning_pod_enabled is False

    res = system.attempt_clone_pod_activation("patient_001")
    assert res["status"] == "CLONING_POD_DEPRECATED_AND_REMOVED"
    assert res["error_code"] == "CLONE_POD_DISMANTLED_TG90754"
    assert "permanently decommissioned" in res["message"]


def test_successful_defibrillation():
    system = PostCloningMedicalCareSystem()
    patient = system.register_patient("patient_clown", "Honk The Clown")
    patient.clinical_state = PatientClinicalState.CARDIAC_ARREST
    patient.organs.heart_integrity = 10.0
    patient.organs.blood_volume_ml = 5000.0
    patient.organs.brain_decay_pct = 15.0

    assert patient.can_defibrillate() is True

    result = system.apply_defibrillator_shock("patient_clown")
    assert result["status"] == "PATIENT_RESUSCITATED"
    assert patient.clinical_state == PatientClinicalState.CONSCIOUS
    assert system.successful_surgical_revivals == 1


def test_defibrillation_failure_modes():
    system = PostCloningMedicalCareSystem()

    # Failure 1: Brain decay exceeds 80% (irreversible brain death)
    p1 = system.register_patient("p_decay", "Brain Decayed")
    p1.clinical_state = PatientClinicalState.CARDIAC_ARREST
    p1.organs.brain_decay_pct = 85.0
    res1 = system.apply_defibrillator_shock("p_decay")
    assert res1["status"] == "DEFIB_FAILED"
    assert "brain decay" in res1["reason"]

    # Failure 2: Severe hypovolemia (< 2500ml blood)
    p2 = system.register_patient("p_hypo", "Exsanguinated")
    p2.clinical_state = PatientClinicalState.CARDIAC_ARREST
    p2.organs.blood_volume_ml = 1200.0
    res2 = system.apply_defibrillator_shock("p_hypo")
    assert res2["status"] == "DEFIB_FAILED"
    assert "blood transfusion" in res2["reason"]


def test_coronary_bypass_surgery():
    system = PostCloningMedicalCareSystem()
    patient = system.register_patient("p_captain", "Captain John Miller")
    patient.clinical_state = PatientClinicalState.CARDIAC_ARREST
    patient.organs.heart_integrity = 5.0

    res = system.perform_coronary_bypass_surgery("p_captain")
    assert res["status"] == "SURGERY_COMPLETED"
    assert patient.organs.heart_integrity == 100.0
    assert patient.clinical_state == PatientClinicalState.CRITICAL_UNCONSCIOUS


def test_cryogenic_stasis_halts_brain_decay():
    system = PostCloningMedicalCareSystem()
    patient = system.register_patient("p_officer", "Security Officer")
    patient.clinical_state = PatientClinicalState.CARDIAC_ARREST
    patient.organs.brain_decay_pct = 20.0

    # Put in cryo tube
    cryo_res = system.place_in_cryo_tube("p_officer")
    assert cryo_res["status"] == "CRYO_STABILIZED"
    assert patient.in_cryo_tube is True

    # Process ticks
    tick_res = system.process_patient_tick("p_officer", delta_s=10.0)
    assert tick_res["status"] == "STABLE_IN_CRYO"
    assert patient.organs.brain_decay_pct == 20.0  # Remained unchanged


def test_biological_decay_tick_without_cryo():
    system = PostCloningMedicalCareSystem()
    patient = system.register_patient("p_miner", "Shaft Miner")
    patient.clinical_state = PatientClinicalState.CARDIAC_ARREST
    patient.organs.brain_decay_pct = 75.0

    tick_res = system.process_patient_tick("p_miner", delta_s=15.0)
    assert tick_res["status"] == "TICK_PROCESSED"
    # Brain decay advances and reaches >= 80% triggering IRREVERSIBLE_BRAIN_DEATH
    assert patient.clinical_state == PatientClinicalState.IRREVERSIBLE_BRAIN_DEATH


def test_dreammaker_removal_patch_syntax():
    system = PostCloningMedicalCareSystem()
    patch = system.export_dreammaker_removal_patch()
    assert "/obj/machinery/clonepod" in patch
    assert "decommissioned cloning pod" in patch
    assert "/obj/item/defibrillator" in patch
    assert "qdel(src)" in patch
