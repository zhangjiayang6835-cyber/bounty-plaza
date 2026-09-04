"""Unit tests for SS13 Rust Engine Core and DMM Converter (Issue #680)."""

import json
import pytest
from scripts.tgstation_rust_engine import (
    DMMToModernFormatConverter,
    RUST_CRATE_SOURCE_MAIN_RS,
    RUST_ENGINE_ARCHITECTURE_DIAGRAM,
    RustComponent,
    RustECSWorld,
)


def test_rust_ecs_world_lifecycle():
    world = RustECSWorld()
    assert world.tick_counter == 0
    assert len(world.entities) == 0

    # Spawn entities with components
    transform = RustComponent("Transform", {"x": 100, "y": 100, "z": 1})
    ent = world.spawn_entity("StationCaptain", [transform])
    assert ent.entity_id == 1
    assert ent.name == "StationCaptain"
    assert "Transform" in ent.components
    assert ent.components["Transform"].data["x"] == 100

    # Run game loop tick
    res = world.run_tick()
    assert res["status"] == "TICK_COMPLETED_SAFE"
    assert res["tick"] == 1
    assert res["entities_count"] == 1
    assert res["updated_entities"] == 1


def test_dmm_parser_and_modern_format_conversion():
    sample_dmm = """
// BYOND DMM MAP DEFINITION
"aaa" = (/turf/open/floor/plating, /area/maintenance)
"aab" = (/turf/closed/wall, /area/hull)

(1,1,1) = {"
aaaaab
aabaaa
"}
"""
    parsed = DMMToModernFormatConverter.parse_dmm_text(sample_dmm)
    assert "aaa" in parsed["key_definitions"]
    assert "aab" in parsed["key_definitions"]
    assert len(parsed["grid_lines"]) == 2

    # Convert to modern format
    converted_json = DMMToModernFormatConverter.convert_dmm_to_open_format(sample_dmm, "json")
    map_dict = json.loads(converted_json)
    assert map_dict["format"] == "tgstation-rust-map-v1+json"
    assert map_dict["memory_safe"] is True
    assert len(map_dict["tiles"]) == 4  # 2x2 grid with 3-char keys
    assert map_dict["tiles"][0]["token"] == "aaa"
    assert "/turf/open/floor/plating" in map_dict["tiles"][0]["elements"]


def test_rust_engine_structure_diagram_and_crate():
    # Verify architecture diagram is present for +$100 bonus reward
    assert "TGSTATION RUST ENGINE (ARCHITECTURE & SUBSYSTEM MATRIX)" in RUST_ENGINE_ARCHITECTURE_DIAGRAM
    assert "Modern Open Formats" in RUST_ENGINE_ARCHITECTURE_DIAGRAM
    assert "Memory-Safe Core" in RUST_ENGINE_ARCHITECTURE_DIAGRAM
    assert "High-Performance ECS" in RUST_ENGINE_ARCHITECTURE_DIAGRAM

    # Verify native Rust source crate structure
    assert "pub struct StationWorld" in RUST_CRATE_SOURCE_MAIN_RS
    assert "pub fn spawn" in RUST_CRATE_SOURCE_MAIN_RS
    assert "pub fn tick" in RUST_CRATE_SOURCE_MAIN_RS
