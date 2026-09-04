"""Unit tests for SS13 Nanites Subsystem & Cellular Biotechnology Engine.
Resolves Issue #632: [BOUNTY] [$666] Add nanites.
Upstream Reference: Iamgoofball/-tg-station#126.
"""

import pytest
from scripts.ss13_nanites_system import (
    SS13NaniteEngine,
    NaniteProgram,
    ProgramCategory,
    HostSpeciesType,
    HostState,
)


@pytest.fixture
def nanite_engine():
    engine = SS13NaniteEngine()
    # Populate Cloud 1 with a Medical Cellular Repair Program
    med_prog = NaniteProgram(
        program_id="cell_repair_1",
        name="Cellular Regeneration",
        category=ProgramCategory.MEDICAL,
        nanite_cost_per_tick=0.5,
        trigger_threshold=50.0,
        effect_magnitude=2.0
    )
    engine.add_program_to_cloud(cloud_id=1, program=med_prog)
    return engine


def test_techweb_unlock_gating(nanite_engine):
    # Military tech fails without illegal_tech scanned
    assert nanite_engine.unlock_tech_node("military_nanites") is False

    # After scanning illegal tech, military unlocked
    nanite_engine.scan_technology("illegal_tech")
    assert nanite_engine.unlock_tech_node("military_nanites") is True

    # Hazard tech fails without alien_tech scanned
    assert nanite_engine.unlock_tech_node("hazard_nanites") is False
    nanite_engine.scan_technology("alien_tech")
    assert nanite_engine.unlock_tech_node("hazard_nanites") is True


def test_nanite_chamber_implantation_and_cloud_sync(nanite_engine):
    nanite_engine.implant_host_via_chamber(
        mob_id="CrewmanBob",
        cloud_id=1,
        safety_threshold=120.0,
        initial_swarm=60.0
    )

    host = nanite_engine.hosts["CrewmanBob"]
    assert host.nanite_count == 60.0
    assert host.safety_threshold == 120.0
    assert host.cloud_id == 1
    assert "cell_repair_1" in host.installed_programs


def test_nanite_purge_via_chamber(nanite_engine):
    nanite_engine.implant_host_via_chamber("CrewmanCharlie", initial_swarm=100.0)
    res = nanite_engine.purge_nanites_via_chamber("CrewmanCharlie")
    assert res["success"] is True
    assert res["extracted_nanites"] == 100.0

    host = nanite_engine.hosts["CrewmanCharlie"]
    assert host.nanite_count == 0.0
    assert len(host.installed_programs) == 0


def test_research_point_generation_by_host_species(nanite_engine):
    # Humanoid Sentient Host: 100% yield
    nanite_engine.register_host("HumanDave", species_type=HostSpeciesType.HUMANOID_SENTIENT, initial_nanites=100.0)
    # Non-Humanoid Host: 50% yield
    nanite_engine.register_host("CorgiIan", species_type=HostSpeciesType.NON_HUMANOID, initial_nanites=100.0)
    # Deceased Host: 10% yield
    nanite_engine.register_host("CorpseZombie", species_type=HostSpeciesType.DECEASED, initial_nanites=100.0)

    res = nanite_engine.process_tick()
    # Human yield: (100+2-0)/100 * 1.0 = 1.02
    # Corgi yield: (100+2-0)/100 * 0.5 = 0.51
    # Corpse yield: (100+2-0)/100 * 0.1 = 0.102
    assert res["total_research_gain"] > 1.5
    assert nanite_engine.research_points == res["total_research_gain"]


def test_medical_program_heals_host_damage(nanite_engine):
    nanite_engine.implant_host_via_chamber("WoundedOfficer", cloud_id=1, initial_swarm=100.0)
    host = nanite_engine.hosts["WoundedOfficer"]
    host.health_damage = 25.0

    # Process tick - cellular regeneration program should trigger and reduce damage
    nanite_engine.process_tick()
    assert host.health_damage == 23.0  # 25 - 2.0


def test_nanite_scanner_diagnostic_readout(nanite_engine):
    nanite_engine.implant_host_via_chamber("PatientAlpha", cloud_id=1, initial_swarm=75.0)
    scan = nanite_engine.scan_host("PatientAlpha")

    assert scan["mob_id"] == "PatientAlpha"
    assert scan["nanite_count"] == 75.0
    assert scan["cloud_id"] == 1
    assert len(scan["installed_programs"]) == 1
    assert scan["installed_programs"][0]["name"] == "Cellular Regeneration"


def test_dreammaker_syntax_export(nanite_engine):
    dm = nanite_engine.export_dreammaker_code()
    assert "/datum/nanite_program" in dm
    assert "/obj/machinery/nanite_chamber" in dm
    assert "/obj/machinery/nanite_public_chamber" in dm
    assert "/obj/item/nanite_scanner" in dm
