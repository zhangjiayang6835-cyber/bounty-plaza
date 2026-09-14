"""Unit tests for Bedrock block schema validation and configuration (Issue #1306)."""

import json
from pathlib import Path
import pytest

from packages.bedrock_block_schema.block_validator import (
    BedrockBlockValidator,
    BlockFace,
    RenderMethod,
)
from packages.bedrock_block_schema.geometry_builder import (
    BlockGeometryBuilder,
)
from packages.bedrock_block_schema.verifier import (
    BedrockBlockVerifier,
)


def test_schema_validation_failure_on_wildcard_face():
    """Verify schema validator catches invalid '*' face on directional block."""
    malformed = BedrockBlockVerifier.create_sample_malformed_block()
    result = BedrockBlockValidator.validate_block_definition(malformed, is_directional=True)

    assert result.is_valid is False
    assert any(
        "Property 'minecraft:material_instances' contains invalid face definition '*'." in err
        for err in result.errors
    )


def test_schema_validation_failure_on_unsupported_render_method():
    """Verify validator flags unsupported render method 'alpha_test_single_side'."""
    malformed = BedrockBlockVerifier.create_sample_malformed_block()
    result = BedrockBlockValidator.validate_block_definition(malformed, is_directional=True)

    assert result.is_valid is False
    assert any(
        "Render method 'alpha_test_single_side' is unsupported under schema 1.21.40." in err
        for err in result.errors
    )


def test_schema_validation_success_modern_1_21_40():
    """Verify modern conforming block definition validates with zero errors."""
    conforming = BedrockBlockVerifier.create_sample_conforming_block()
    result = BedrockBlockValidator.validate_block_definition(conforming, is_directional=True)

    assert result.is_valid is True
    assert len(result.errors) == 0
    assert result.has_seamless_outline is True
    assert result.format_version == "1.21.40"
    assert result.identifier == "custom:void_crystal_ore"


def test_schema_validation_forward_compatibility_1_26_x():
    """Verify forward-compatibility across modern Bedrock versions including 1.26.x."""
    conforming = BedrockBlockVerifier.create_sample_conforming_block()
    for ver in ("1.21.50", "1.26.0", "1.26.10"):
        conforming["format_version"] = ver
        result = BedrockBlockValidator.validate_block_definition(conforming, is_directional=True)
        assert result.is_valid is True
        assert len(result.errors) == 0


def test_face_specific_directional_mapping():
    """Verify all six cube faces are explicitly defined with directional textures."""
    conforming = BedrockBlockVerifier.create_sample_conforming_block()
    instances = conforming["minecraft:block"]["components"]["minecraft:material_instances"]

    assert len(instances) == 6
    for face in ("up", "down", "north", "south", "east", "west"):
        assert face in instances
        assert "texture" in instances[face]

    assert instances["up"]["texture"] == "void_crystal_ore_top"
    assert instances["down"]["texture"] == "void_crystal_ore_bottom"
    assert instances["north"]["texture"] == "void_crystal_ore_side"


def test_render_method_alpha_test_configured():
    """Verify render method is strictly set to alpha_test across all faces."""
    conforming = BedrockBlockVerifier.create_sample_conforming_block()
    instances = conforming["minecraft:block"]["components"]["minecraft:material_instances"]

    for face, conf in instances.items():
        assert conf["render_method"] == RenderMethod.ALPHA_TEST.value
        assert conf["face_dimming"] is True
        assert conf["ambient_occlusion"] is True


def test_isotropic_property_flag():
    """Verify isotropic flag is explicitly configured False for directional ore textures."""
    conforming = BedrockBlockVerifier.create_sample_conforming_block()
    instances = conforming["minecraft:block"]["components"]["minecraft:material_instances"]

    for face, conf in instances.items():
        assert conf["isotropic"] is False


def test_seamless_selection_box_alignment():
    """Verify selection box and collision box align precisely to standard unit cube."""
    conforming = BedrockBlockVerifier.create_sample_conforming_block()
    components = conforming["minecraft:block"]["components"]

    sel_box = components["minecraft:selection_box"]
    col_box = components["minecraft:collision_box"]

    assert sel_box["origin"] == [-8.0, 0.0, -8.0]
    assert sel_box["size"] == [16.0, 16.0, 16.0]
    assert col_box["origin"] == [-8.0, 0.0, -8.0]
    assert col_box["size"] == [16.0, 16.0, 16.0]


def test_divergent_selection_box_rejected():
    """Verify misaligned selection box is rejected to prevent visual outline seams."""
    conforming = BedrockBlockVerifier.create_sample_conforming_block()
    conforming["minecraft:block"]["components"]["minecraft:selection_box"] = {
        "origin": [-7.0, 0.0, -7.0],
        "size": [14.0, 14.0, 14.0],
    }

    result = BedrockBlockValidator.validate_block_definition(conforming)
    assert result.is_valid is False
    assert result.has_seamless_outline is False
    assert any("diverges from standard unit cube bounds" in err for err in result.errors)


def test_geometry_builder_unit_cube():
    """Verify geometry builder creates valid Bedrock geometry with face UV mappings."""
    geo_data = BlockGeometryBuilder.create_unit_cube_geometry("geometry.void_crystal_ore")
    validation = BlockGeometryBuilder.validate_geometry(
        geo_data, expected_identifier="geometry.void_crystal_ore"
    )

    assert validation.is_valid is True
    assert len(validation.errors) == 0
    assert validation.origin == [-8.0, 0.0, -8.0]
    assert validation.size == [16.0, 16.0, 16.0]


def test_migration_converts_malformed_definition():
    """Verify migration engine transforms invalid block JSON to compliant schema."""
    malformed = BedrockBlockVerifier.create_sample_malformed_block()
    migrated = BedrockBlockValidator.migrate_definition(
        malformed, default_render_method=RenderMethod.ALPHA_TEST.value
    )

    result = BedrockBlockValidator.validate_block_definition(migrated, is_directional=True)
    assert result.is_valid is True
    assert len(result.errors) == 0
    assert result.has_seamless_outline is True


def test_verifier_all_six_invariants_pass():
    """Verify BedrockBlockVerifier reports 6/6 passing invariants on conforming block."""
    conforming = BedrockBlockVerifier.create_sample_conforming_block()
    geo_data = BlockGeometryBuilder.create_unit_cube_geometry("geometry.void_crystal_ore")
    terrain = {
        "texture_data": {
            "void_crystal_ore_top": {"textures": "textures/blocks/void_crystal_ore_top"},
            "void_crystal_ore_bottom": {"textures": "textures/blocks/void_crystal_ore_bottom"},
            "void_crystal_ore_side": {"textures": "textures/blocks/void_crystal_ore_side"},
        }
    }

    report = BedrockBlockVerifier.verify_all_invariants(conforming, geo_data, terrain)
    assert report.is_successful is True
    assert report.passed_invariants == 6
    assert report.failed_invariants == 0
    assert len(report.failure_reasons) == 0


def test_verifier_detects_malformed_definition_failures():
    """Verify BedrockBlockVerifier flags multiple failures on original malformed block."""
    malformed = BedrockBlockVerifier.create_sample_malformed_block()
    report = BedrockBlockVerifier.verify_all_invariants(malformed)

    assert report.is_successful is False
    assert report.failed_invariants > 0
    assert any("invalid face definition '*'" in r.lower() for r in report.failure_reasons)
    assert any("alpha_test_single_side" in r for r in report.failure_reasons)


def test_pack_files_on_disk_validation():
    """Verify actual disk files in packs/ directory conform to all invariants."""
    bp_block_path = Path("packs/BP/blocks/void_crystal_ore.json")
    geo_path = Path("packs/RP/models/blocks/void_crystal_ore.geo.json")
    terrain_path = Path("packs/RP/textures/terrain_texture.json")

    assert bp_block_path.exists()
    assert geo_path.exists()
    assert terrain_path.exists()

    with open(bp_block_path, encoding="utf-8") as f:
        block_def = json.load(f)
    with open(geo_path, encoding="utf-8") as f:
        geo_data = json.load(f)
    with open(terrain_path, encoding="utf-8") as f:
        terrain_data = json.load(f)

    report = BedrockBlockVerifier.verify_all_invariants(block_def, geo_data, terrain_data)
    assert report.is_successful is True
    assert report.passed_invariants == 6
    assert report.failed_invariants == 0
