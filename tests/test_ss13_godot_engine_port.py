"""Unit tests for BYOND DM to Godot 4 Engine Port.
Resolves Issue #651: [BOUNTY] [$10000] Ported Space Station 13 to the Godot Engine.
Upstream Reference: Iamgoofball/-tg-station#173.
"""

import pytest
from scripts.ss13_godot_engine_port import (
    SS13GodotEnginePort,
    TranspiledClass,
    MULTILINGUAL_MANIFESTOS,
)


@pytest.fixture
def port_engine():
    return SS13GodotEnginePort()


def test_core_engine_nodes_generation(port_engine):
    classes = port_engine.transpiled_classes

    # Verify /datum -> Datum (RefCounted)
    assert "/datum" in classes
    datum_node = classes["/datum"]
    assert datum_node.godot_class_name == "Datum"
    assert datum_node.extends_class == "RefCounted"
    assert "class_name Datum" in datum_node.gdscript_source
    assert "func qdel()" in datum_node.gdscript_source

    # Verify SScontroller -> MasterController (Node)
    assert "/datum/controller/subsystem" in classes
    mc_node = classes["/datum/controller/subsystem"]
    assert mc_node.godot_class_name == "MasterController"
    assert "func _physics_process" in mc_node.gdscript_source

    # Verify Human Mob -> HumanMob (CharacterBody2D)
    assert "/mob/living/carbon/human" in classes
    mob_node = classes["/mob/living/carbon/human"]
    assert mob_node.godot_class_name == "HumanMob"
    assert mob_node.extends_class == "CharacterBody2D"
    assert "inventory: Dictionary" in mob_node.gdscript_source
    assert "move_and_slide()" in mob_node.gdscript_source


def test_transpile_dm_to_gdscript(port_engine):
    dm_sample = (
        "// Player health management proc\n"
        "var/health = 100\n"
        "var/max_health = 100\n"
        "/proc/apply_damage(amount)\n"
        "health -= amount\n"
        "return health\n"
    )

    gd = port_engine.transpile_dm_to_gdscript(dm_sample)
    assert "# Player health management proc" in gd
    assert "var health = 100" in gd
    assert "var max_health = 100" in gd
    assert "func apply_damage(amount):" in gd
    assert "return health" in gd


def test_linda_atmospheric_diffusion(port_engine):
    # Equalizing pressurized tile (100 moles @ 300K) with vacuum tile (0 moles @ 0K)
    res = port_engine.simulate_linda_atmos_diffusion(
        tile_a_moles=100.0,
        tile_a_temp_k=300.0,
        tile_b_moles=0.0,
        tile_b_temp_k=0.0,
        diffusion_rate=0.25
    )

    assert res["status"] == "EQUALIZED"
    assert res["tile_a"]["moles"] == 75.0
    assert res["tile_b"]["moles"] == 25.0
    assert res["tile_a"]["temp_k"] == 300.0
    assert res["tile_b"]["temp_k"] == 300.0
    assert res["pressure_differential"] > 0


def test_godot_project_config_generation(port_engine):
    cfg = port_engine.generate_godot_project_config()
    assert 'config/name="SpaceStation13-Godot"' in cfg
    assert 'run/main_scene="res://scenes/station_master.tscn"' in cfg
    assert "viewport_width=1280" in cfg
    assert "viewport_height=720" in cfg
    assert "move_left=" in cfg


def test_multilingual_manifesto_completeness(port_engine):
    manifestos = port_engine.get_multilingual_manifesto()
    assert "en" in manifestos
    assert "ru" in manifestos
    assert "zh" in manifestos
    assert "es" in manifestos
    assert "Space Station 13" in manifestos["en"]
    assert "BYOND" in manifestos["ru"]
    assert "Godot" in manifestos["zh"]
    assert "motor central" in manifestos["es"]
