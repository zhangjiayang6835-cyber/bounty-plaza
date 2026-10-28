"""Unit tests for Space Station 13 Unreal Engine 5 Architecture & Core Systems.
Resolves Issue #646: [BOUNTY] [IMPORTANT] [$50000] [AGENTIC / Opire] Rewrite entire SS13 on Unreal Engine 5.
Upstream Reference: Iamgoofball/-tg-station#143.
"""

import json
import pytest
from scripts.ss13_ue5_architecture import (
    SS13UE5Architecture,
    AntagonistType,
    LimbType,
    LimbHealth,
    AtmosCell,
)


@pytest.fixture
def ue5_arch():
    arch = SS13UE5Architecture(project_name="SpaceStation13")
    arch.initialize_atmos_grid(size_x=5, size_y=5)
    return arch


def test_atmos_grid_initialization_and_pressure(ue5_arch):
    assert len(ue5_arch.atmos_grid) == 25
    cell = ue5_arch.atmos_grid["0_0"]
    assert cell.oxygen_moles == 21.8
    assert cell.nitrogen_moles == 82.2
    assert cell.pressure_kpa > 100.0  # Approx 101.3 kPa standard station atmosphere


def test_explosive_vacuum_breach(ue5_arch):
    breach = ue5_arch.trigger_vacuum_breach(2, 2)
    assert breach["event"] == "EXPLOSIVE_HULL_BREACH"
    assert breach["initial_pressure_kpa"] > 100.0
    assert breach["final_pressure_kpa"] == 0.0
    assert breach["final_temp_k"] == 2.7
    assert breach["is_vacuum"] is True


def test_powernet_simulation_and_smes(ue5_arch):
    # Surplus generation: 50 kW gen vs 30 kW consumption -> +20 kW to SMES
    res_surplus = ue5_arch.simulate_powernet_cycle(generation_watts=50000.0, consumption_watts=30000.0)
    assert res_surplus["net_surplus_kw"] == 20.0
    assert res_surplus["brownout_warning"] is False
    assert res_surplus["smes_stored_mj"] > 5.0

    # Deficit draining SMES
    res_deficit = ue5_arch.simulate_powernet_cycle(generation_watts=0.0, consumption_watts=10000000.0)
    assert res_deficit["brownout_warning"] is True
    assert res_deficit["smes_stored_mj"] == 0.0


def test_medical_targeted_limb_damage_and_consciousness(ue5_arch):
    char = ue5_arch.create_character_medical_state("Engineer Dave")
    assert char["is_conscious"] is True
    assert len(char["limbs"]) == 6

    # Apply moderate damage to head
    hit1 = ue5_arch.apply_targeted_damage(char, LimbType.HEAD, brute=40.0, burn=0.0)
    assert hit1["damaged_limb"] == "head"
    assert hit1["limb_health"] == 60.0
    assert hit1["is_conscious"] is True

    # Apply catastrophic damage exceeding 200 total damage threshold
    hit2 = ue5_arch.apply_targeted_damage(char, LimbType.TORSO, brute=180.0, burn=0.0)
    assert hit2["total_damage"] == 220.0
    assert hit2["is_conscious"] is False
    assert char["is_conscious"] is False


def test_antagonist_role_assignment(ue5_arch):
    traitor = ue5_arch.assign_antagonist_role(
        char_name="Bartender Bob",
        antag_type=AntagonistType.TRAITOR,
        assigned_objectives=["Assassinate the Captain", "Escape alive on shuttle"]
    )
    assert traitor["assigned_successfully"] is True
    assert "Syndicate Uplink" in traitor["antagonist_role"]
    assert traitor["uplink_code"] == "143.7 Alpha"
    assert len(traitor["objectives"]) == 2

    cult = ue5_arch.assign_antagonist_role(
        char_name="Chaplain Marcus",
        antag_type=AntagonistType.CULT,
        assigned_objectives=["Summon Nar'Sie"]
    )
    assert "Blood Cult" in cult["antagonist_role"]
    assert cult["uplink_code"] is None


def test_ue5_project_manifest_and_atmos_header(ue5_arch):
    manifest_str = ue5_arch.generate_ue5_project_manifest()
    manifest = json.loads(manifest_str)
    assert manifest["EngineAssociation"] == "5.4"
    assert manifest["Modules"][0]["Name"] == "SpaceStation13"

    header = ue5_arch.generate_ue5_atmos_header()
    assert "class SPACESTATION13_API USS13AtmosSubsystem" in header
    assert "struct SPACESTATION13_API FSS13GasMixture" in header
    assert "UWorldSubsystem" in header
