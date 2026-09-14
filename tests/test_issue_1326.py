"""Pytest test suite verifying Issue #1326 block schema validation and isotropic rendering."""

import json
from pathlib import Path
import pytest

from packages.bedrock_block_validator.generator import BedrockBlockGenerator
from packages.bedrock_block_validator.migrator import BedrockBlockMigrator
from packages.bedrock_block_validator.models import (
    BedrockBlockDefinition,
    BlockComponents,
    BlockDescription,
    MaterialInstance,
    RenderMethod,
)
from packages.bedrock_block_validator.validator import BedrockBlockSchemaValidator

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_schema_validator_reproduces_and_flags_invalid_wildcard_alpha_test() -> None:
    """Ensure validator catches wildcard material instance with alpha_test render method."""
    broken_definition = {
        "format_version": "1.21.40",
        "minecraft:block": {
            "description": {
                "identifier": "custom:compressed_basalt",
            },
            "components": {
                "minecraft:material_instances": {
                    "*": {
                        "texture": "compressed_basalt_side",
                        "render_method": "alpha_test",
                    }
                }
            },
        },
    }

    report = BedrockBlockSchemaValidator.validate_json_dict(broken_definition)
    assert report.is_valid is False
    assert report.has_code("INVALID_WILDCARD_ALPHA_TEST")
    assert any("alpha_test" in msg for msg in report.error_messages())


def test_schema_validator_flags_isotropic_in_description() -> None:
    """Ensure validator rejects placement of isotropic flag under description object."""
    invalid_definition = {
        "format_version": "1.21.50",
        "minecraft:block": {
            "description": {
                "identifier": "custom:compressed_basalt",
                "isotropic": True,
            },
            "components": {
                "minecraft:material_instances": {
                    "*": {
                        "texture": "compressed_basalt_side",
                        "render_method": "opaque",
                    }
                }
            },
        },
    }

    report = BedrockBlockSchemaValidator.validate_json_dict(invalid_definition)
    assert report.is_valid is False
    assert report.has_code("ISOTROPIC_IN_DESCRIPTION")


def test_schema_validator_validates_compressed_basalt_json_file() -> None:
    """Verify repository blocks/compressed_basalt.json passes all schema validation gates."""
    block_path = ROOT_DIR / "blocks" / "compressed_basalt.json"
    assert block_path.is_file()

    report = BedrockBlockSchemaValidator.validate_file(block_path)
    assert report.is_valid is True
    assert len(report.issues) == 0


def test_compressed_basalt_components_and_isotropic_invariants() -> None:
    """Verify material instances configure isotropic rotation strictly on up and down faces."""
    block_path = ROOT_DIR / "blocks" / "compressed_basalt.json"
    with open(block_path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)

    assert doc["format_version"] == "1.21.50"
    block = doc["minecraft:block"]
    assert block["description"]["identifier"] == "custom:compressed_basalt"
    assert "isotropic" not in block["description"]

    components = block["components"]
    assert components["minecraft:destructible_by_mining"]["seconds_to_destroy"] == 2.5
    assert components["minecraft:destructible_by_explosion"]["explosion_resistance"] == 6.0
    assert components["minecraft:friction"] == 0.6
    assert components["minecraft:map_color"] == "#474F52"
    assert components["minecraft:selection_box"]["size"] == [16, 16, 16]
    assert components["minecraft:collision_box"]["size"] == [16, 16, 16]
    assert components["minecraft:geometry"]["identifier"] == "geometry.compressed_basalt"

    mat_instances = components["minecraft:material_instances"]
    required_faces = ["up", "down", "north", "south", "east", "west", "*"]
    for face in required_faces:
        assert face in mat_instances
        assert mat_instances[face]["render_method"] == "opaque"
        assert mat_instances[face]["ambient_occlusion"] == 1.0
        assert mat_instances[face]["face_dimming"] is True

    assert mat_instances["up"]["isotropic"] is True
    assert mat_instances["down"]["isotropic"] is True
    assert "isotropic" not in mat_instances["north"]
    assert "isotropic" not in mat_instances["south"]


def test_block_generator_output_conforms_to_schema() -> None:
    """Verify generated block definition passes schema validator with zero issues."""
    generated = BedrockBlockGenerator.create_compressed_basalt_dict()
    report = BedrockBlockSchemaValidator.validate_compressed_basalt_dict(generated)
    assert report.is_valid is True
    assert len(report.issues) == 0


def test_migrator_transforms_invalid_legacy_definition() -> None:
    """Verify BedrockBlockMigrator corrects legacy schema flaws into compliant structures."""
    broken_definition = {
        "format_version": "1.21.40",
        "minecraft:block": {
            "description": {
                "identifier": "custom:compressed_basalt",
                "isotropic": True,
            },
            "components": {
                "minecraft:material_instances": {
                    "*": {
                        "texture": "compressed_basalt_side",
                        "render_method": "alpha_test",
                    }
                }
            },
        },
    }

    initial_report = BedrockBlockSchemaValidator.validate_json_dict(broken_definition)
    assert initial_report.is_valid is False

    migrated = BedrockBlockMigrator.migrate_definition(broken_definition)
    final_report = BedrockBlockSchemaValidator.validate_compressed_basalt_dict(migrated)

    assert final_report.is_valid is True
    assert migrated["format_version"] == "1.21.50"
    assert "isotropic" not in migrated["minecraft:block"]["description"]
    assert migrated["minecraft:block"]["components"]["minecraft:material_instances"]["*"]["render_method"] == "opaque"
    assert migrated["minecraft:block"]["components"]["minecraft:material_instances"]["up"]["isotropic"] is True
    assert migrated["minecraft:block"]["components"]["minecraft:material_instances"]["down"]["isotropic"] is True


def test_supporting_culling_rules_conformance() -> None:
    """Verify culling rules file correctly maps all 6 face directions."""
    culling_path = ROOT_DIR / "block_culling" / "compressed_basalt.culling.json"
    assert culling_path.is_file()

    with open(culling_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    rules_root = data.get("minecraft:block_culling_rules", {})
    assert rules_root.get("description", {}).get("identifier") == "custom:compressed_basalt_culling"

    rules = rules_root.get("rules", [])
    assert len(rules) == 6
    directions = {r["direction"] for r in rules}
    assert directions == {"up", "down", "north", "south", "east", "west"}


def test_supporting_geometry_model_conformance() -> None:
    """Verify block geometry model defines standard 16x16x16 bounds and cube UVs."""
    geo_path = ROOT_DIR / "models" / "blocks" / "compressed_basalt.geo.json"
    assert geo_path.is_file()

    with open(geo_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    geometries = data.get("minecraft:geometry", [])
    assert len(geometries) > 0
    geo = geometries[0]
    assert geo["description"]["identifier"] == "geometry.compressed_basalt"

    cubes = geo["bones"][0]["cubes"]
    assert len(cubes) == 1
    assert cubes[0]["size"] == [16, 16, 16]
    uv = cubes[0]["uv"]
    assert set(uv.keys()) == {"up", "down", "north", "south", "east", "west"}


def test_supporting_terrain_texture_atlas_conformance() -> None:
    """Verify terrain texture atlas properly defines top, bottom, and side textures."""
    atlas_path = ROOT_DIR / "textures" / "terrain_texture.json"
    assert atlas_path.is_file()

    with open(atlas_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    texture_data = data.get("texture_data", {})
    assert "compressed_basalt_top" in texture_data
    assert "compressed_basalt_bottom" in texture_data
    assert "compressed_basalt_side" in texture_data


def test_manifest_engine_version_conformance() -> None:
    """Verify behavior/resource pack manifest targets Bedrock 1.21.50+."""
    manifest_path = ROOT_DIR / "manifest.json"
    assert manifest_path.is_file()

    with open(manifest_path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    min_engine = manifest.get("header", {}).get("min_engine_version", [])
    assert min_engine >= [1, 21, 50]
    dependencies = manifest.get("dependencies", [])
    assert any(dep.get("module_name") == "@minecraft/server" for dep in dependencies)


def test_model_roundtrip_serialization() -> None:
    """Verify BedrockBlockDefinition data model serializes to compliant dictionary."""
    model = BedrockBlockDefinition(
        format_version="1.21.50",
        description=BlockDescription(identifier="test:block"),
        components=BlockComponents(
            material_instances={
                "*": MaterialInstance(
                    texture="test_texture",
                    render_method=RenderMethod.OPAQUE,
                )
            }
        ),
    )
    serialized = model.to_dict()
    assert serialized["format_version"] == "1.21.50"
    assert serialized["minecraft:block"]["description"]["identifier"] == "test:block"
    assert serialized["minecraft:block"]["components"]["minecraft:material_instances"]["*"]["render_method"] == "opaque"


def test_schema_validator_rejects_missing_mandatory_fields() -> None:
    """Verify validator flags missing format_version, missing root, or bad identifiers."""
    no_version = {"minecraft:block": {"description": {"identifier": "a:b"}, "components": {}}}
    report1 = BedrockBlockSchemaValidator.validate_json_dict(no_version)
    assert report1.is_valid is False
    assert report1.has_code("MISSING_FORMAT_VERSION")

    no_block = {"format_version": "1.21.50"}
    report2 = BedrockBlockSchemaValidator.validate_json_dict(no_block)
    assert report2.is_valid is False
    assert report2.has_code("MISSING_BLOCK_ROOT")

    bad_id = {
        "format_version": "1.21.50",
        "minecraft:block": {
            "description": {"identifier": "unnamespaced_block"},
            "components": {},
        },
    }
    report3 = BedrockBlockSchemaValidator.validate_json_dict(bad_id)
    assert report3.is_valid is False
    assert report3.has_code("INVALID_IDENTIFIER")
