"""Unit, diagnostics, and job design test suite for the Fish Doctor medical role 🐟.
Resolves Issue #650: [BOUNTY] [READY FOR AGENT] [200-600$USD Opire] Implement the 'Fish Doctor' job 🐟.
"""

import pytest
from scripts.fish_doctor_job import (
    AquaticOrganism,
    FishDoctorJob,
    FishDoctorKit,
    FishHealthState,
    BYOND_FISH_DOCTOR_DM_SOURCE,
)


@pytest.fixture
def carp():
    """Returns a test aquatic organism representing an unruly space carp."""
    return AquaticOrganism(
        organism_id="carp_specimen_01",
        species="Space Carp",
        name="Barnaby",
        health=100.0,
        max_health=100.0,
        dissolved_oxygen_pct=95.0,
        salinity_optimum=35.0,
        current_salinity=35.0,
        parasites_count=0,
    )


@pytest.fixture
def doctor_kit():
    """Returns an initialized Fish Doctor medical equipment kit."""
    return FishDoctorKit()


@pytest.fixture
def job_spec():
    """Returns the architectural job specification for the Fish Doctor."""
    return FishDoctorJob()


def test_fish_health_state_transitions(carp):
    """Verifies that patient health state accurately reflects physiological stresses."""
    assert carp.health_state == FishHealthState.HEALTHY

    # Parasite infestation
    carp.parasites_count = 3
    assert carp.health_state == FishHealthState.PARASITIZED

    # Salinity shock overrides parasite status
    carp.parasites_count = 0
    carp.current_salinity = 10.0  # Deviation > 10 PSU
    assert carp.health_state == FishHealthState.SALINITY_SHOCK

    # Oxygen deprivation
    carp.current_salinity = 35.0
    carp.dissolved_oxygen_pct = 40.0
    assert carp.health_state == FishHealthState.OXYGEN_DEPRIVED

    # Critical health
    carp.health = 15.0
    assert carp.health_state == FishHealthState.CRITICAL

    # Deceased
    carp.health = 0.0
    assert carp.health_state == FishHealthState.DECEASED


def test_vitals_scanning_telemetry(carp, doctor_kit):
    """Verifies diagnostic scanning data structure and formatting."""
    carp.take_wound(brute=15.0, burn=10.0)
    report = doctor_kit.scan_fish_vitals(carp)

    assert report["name"] == "Barnaby"
    assert report["species"] == "Space Carp"
    assert report["health"] == 75.0
    assert report["wounds"]["brute"] == 15.0
    assert report["wounds"]["burn"] == 10.0
    assert report["state"] == FishHealthState.HEALTHY.value


def test_parasite_clearing_treatment(carp, doctor_kit):
    """Verifies successful removal of gill parasites and dose tracking."""
    carp.parasites_count = 4
    carp.health = 80.0

    res = doctor_kit.treat_parasites(carp)

    assert res["success"] is True
    assert res["parasites_cleared"] == 4
    assert carp.parasites_count == 0
    assert carp.health == 100.0
    assert doctor_kit.anti_parasite_applicators == 4


def test_saline_oxygen_bath_restoration(carp, doctor_kit):
    """Verifies water chemistry equilibrium restoration."""
    carp.current_salinity = 15.0
    carp.dissolved_oxygen_pct = 30.0

    res = doctor_kit.administer_saline_oxygen_bath(carp)

    assert res["success"] is True
    assert carp.current_salinity == 35.0
    assert carp.dissolved_oxygen_pct == 100.0
    assert doctor_kit.saline_doses == 9


def test_chitin_ointment_wound_healing(carp, doctor_kit):
    """Verifies topical ointment accelerates brute and burn tissue recovery."""
    carp.take_wound(brute=20.0, burn=20.0)
    assert carp.health == 60.0

    res = doctor_kit.apply_chitin_ointment(carp, amount_ml=20.0)

    assert res["success"] is True
    assert res["healed_brute"] == 20.0
    assert res["healed_burn"] == 20.0
    assert carp.health == 100.0
    assert doctor_kit.chitin_ointment_ml == 80.0


def test_job_specification_roles_and_access(job_spec):
    """Verifies departmental affiliations, department heads, and security permissions."""
    assert job_spec.title == "Fish Doctor"
    assert job_spec.department == "Medical"
    assert job_spec.total_positions == 1
    assert "Chief Medical Officer" in job_spec.supervisors
    # Medical (20), Surgery (23), and Xenobiology (47) access
    assert 20 in job_spec.access_levels
    assert 23 in job_spec.access_levels
    assert 47 in job_spec.access_levels
    assert "galoshes/waterproof" in job_spec.outfit["shoes"]


def test_byond_dm_job_definition_syntax():
    """Verifies DM code declarations for /datum/job/fish_doctor and tools."""
    assert "/datum/job/fish_doctor" in BYOND_FISH_DOCTOR_DM_SOURCE
    assert "department_head = list(\"Chief Medical Officer\")" in BYOND_FISH_DOCTOR_DM_SOURCE
    assert "/obj/item/fish_stethoscope" in BYOND_FISH_DOCTOR_DM_SOURCE
    assert "ACCESS_XENOBIOLOGY" in BYOND_FISH_DOCTOR_DM_SOURCE
