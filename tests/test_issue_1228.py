"""Comprehensive unit and acceptance tests for Issue #1228."""

import json
from pathlib import Path
import pytest

from packages.bedrock_humanoid_npc.models import (
    BoneDefinition,
    ClientEntityDefinition,
    CubeDefinition,
    ValidationReport,
)
from packages.bedrock_humanoid_npc.validator import (
    GeometryModelAnalyzer,
    HumanoidEntityValidator,
)
from packages.bedrock_humanoid_npc.migration import EntityMigrationPipeline

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_entity_file_exists():
    """Verify that the client entity file exists on disk."""
    path = ROOT_DIR / "RP" / "entity" / "custom_npc.entity.json"
    assert path.is_file(), "custom_npc.entity.json must exist"


def test_entity_schema_and_modern_geometry():
    """Verify client entity uses modern humanoid geometry and render controller."""
    path = ROOT_DIR / "RP" / "entity" / "custom_npc.entity.json"
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    validator = HumanoidEntityValidator()
    report = validator.validate_entity_dict(data, source_path=str(path))
    assert report.is_valid, f"Entity validation failed: {[i.message for i in report.issues]}"

    desc = data["minecraft:client_entity"]["description"]
    assert desc["identifier"] == "custom:npc"
    assert desc["geometry"]["default"] == "geometry.humanoid.custom"
    assert "controller.render.default" in desc["render_controllers"]
    assert "controller.render.zombie" not in desc["render_controllers"]
    assert desc["materials"]["default"] == "entity_alphatest"


def test_geometry_file_exists():
    """Verify that the custom NPC geometry model file exists on disk."""
    path = ROOT_DIR / "RP" / "models" / "entity" / "custom_npc.geo.json"
    assert path.is_file(), "custom_npc.geo.json must exist"


def test_geometry_texture_dimensions():
    """Verify that geometry texture dimensions are 64x64 for modern player skins."""
    path = ROOT_DIR / "RP" / "models" / "entity" / "custom_npc.geo.json"
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    geo_item = data["minecraft:geometry"][0]
    desc = geo_item["description"]
    assert desc["texture_width"] == 64
    assert desc["texture_height"] == 64


def test_asymmetric_limb_uv_mapping():
    """Verify that left arm and leg have independent UVs and no mirror flags."""
    path = ROOT_DIR / "RP" / "models" / "entity" / "custom_npc.geo.json"
    analyzer = GeometryModelAnalyzer()
    report = analyzer.analyze_geometry_file(path)

    assert report.is_valid, f"Geometry validation failed: {[i.message for i in report.issues]}"
    assert report.asymmetric_limbs_supported, "Asymmetric limb UV mapping must be supported"

    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    bones = {b["name"]: b for b in data["minecraft:geometry"][0]["bones"]}
    right_arm_uv = bones["rightArm"]["cubes"][0]["uv"]
    left_arm_uv = bones["leftArm"]["cubes"][0]["uv"]
    assert right_arm_uv != left_arm_uv, "Left arm must not duplicate right arm UV"
    assert bones["leftArm"].get("mirror", False) is False

    right_leg_uv = bones["rightLeg"]["cubes"][0]["uv"]
    left_leg_uv = bones["leftLeg"]["cubes"][0]["uv"]
    assert right_leg_uv != left_leg_uv, "Left leg must not duplicate right leg UV"
    assert bones["leftLeg"].get("mirror", False) is False


def test_dual_layer_outer_skin_geometry():
    """Verify all 6 dual-layer outer skin bones exist with proper inflation."""
    path = ROOT_DIR / "RP" / "models" / "entity" / "custom_npc.geo.json"
    analyzer = GeometryModelAnalyzer()
    report = analyzer.analyze_geometry_file(path)

    assert report.dual_layer_supported, "Dual layer outer geometry must be verified"

    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    bones = {b["name"]: b for b in data["minecraft:geometry"][0]["bones"]}
    required_outer = ["hat", "jacket", "rightSleeve", "leftSleeve", "rightPants", "leftPants"]
    for outer_bone in required_outer:
        assert outer_bone in bones, f"Outer bone {outer_bone} must exist"
        cube = bones[outer_bone]["cubes"][0]
        assert cube.get("inflate", 0.0) >= 0.25, f"{outer_bone} cube must have positive inflation"


def test_asymmetric_outer_sleeve_and_pants_uv():
    """Verify outer sleeves and outer pants use unique asymmetric UV offsets."""
    path = ROOT_DIR / "RP" / "models" / "entity" / "custom_npc.geo.json"
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    bones = {b["name"]: b for b in data["minecraft:geometry"][0]["bones"]}
    assert bones["leftSleeve"]["cubes"][0]["uv"] != bones["rightSleeve"]["cubes"][0]["uv"]
    assert bones["leftPants"]["cubes"][0]["uv"] != bones["rightPants"]["cubes"][0]["uv"]


def test_validator_rejects_legacy_zombie_definition():
    """Verify validator flags legacy zombie geometry and controllers with errors."""
    legacy_entity = {
        "format_version": "1.10.0",
        "minecraft:client_entity": {
            "description": {
                "identifier": "custom:npc",
                "materials": {"default": "entity_alphatest"},
                "textures": {"default": "textures/entity/custom_npc"},
                "geometry": {"default": "geometry.zombie.v1.8"},
                "render_controllers": ["controller.render.zombie"],
            }
        },
    }
    validator = HumanoidEntityValidator()
    report = validator.validate_entity_dict(legacy_entity)

    assert not report.is_valid
    codes = [issue.code for issue in report.issues]
    assert "LEGACY_GEOMETRY_DETECTED" in codes
    assert "INCOMPATIBLE_RENDER_CONTROLLER" in codes


def test_geometry_analyzer_catches_mirrored_limbs():
    """Verify geometry analyzer identifies duplicate UVs and mirror flags."""
    bad_geo = {
        "format_version": "1.12.0",
        "minecraft:geometry": [
            {
                "description": {"identifier": "geometry.test", "texture_width": 64, "texture_height": 64},
                "bones": [
                    {"name": "rightArm", "cubes": [{"origin": [-8, 12, -2], "size": [4, 12, 4], "uv": [40, 16]}]},
                    {"name": "leftArm", "mirror": True, "cubes": [{"origin": [4, 12, -2], "size": [4, 12, 4], "uv": [40, 16]}]},
                    {"name": "rightLeg", "cubes": [{"origin": [-4, 0, -2], "size": [4, 12, 4], "uv": [0, 16]}]},
                    {"name": "leftLeg", "mirror": True, "cubes": [{"origin": [0, 0, -2], "size": [4, 12, 4], "uv": [0, 16]}]},
                ],
            }
        ],
    }
    analyzer = GeometryModelAnalyzer()
    report = analyzer.analyze_geometry_dict(bad_geo)

    assert not report.is_valid
    codes = [issue.code for issue in report.issues]
    assert "MIRRORED_ARM_UV" in codes
    assert "MIRRORED_ARM_FLAG" in codes
    assert "MIRRORED_LEG_UV" in codes
    assert "MIRRORED_LEG_FLAG" in codes
    assert not report.asymmetric_limbs_supported


def test_migration_pipeline_execution(tmp_path):
    """Verify migration pipeline properly transforms legacy entity to modern format."""
    legacy_file = tmp_path / "legacy_npc.json"
    target_file = tmp_path / "migrated_npc.json"
    legacy_content = {
        "format_version": "1.8.0",
        "minecraft:client_entity": {
            "description": {
                "identifier": "custom:migrated_npc",
                "materials": {"default": "entity_alphatest"},
                "textures": {"default": "textures/entity/custom_npc"},
                "geometry": {"default": "geometry.zombie.v1.8"},
                "render_controllers": ["controller.render.zombie"],
            }
        },
    }
    with open(legacy_file, "w", encoding="utf-8") as handle:
        json.dump(legacy_content, handle)

    pipeline = EntityMigrationPipeline()
    result = pipeline.migrate_entity_file(legacy_file, target_file)

    assert target_file.is_file()
    assert result["format_version"] == "1.10.0"
    desc = result["minecraft:client_entity"]["description"]
    assert desc["geometry"]["default"] == "geometry.humanoid.custom"
    assert desc["render_controllers"] == ["controller.render.default"]


def test_model_roundtrips():
    """Verify dataclass instantiation and dictionary parsing."""
    cube = CubeDefinition.from_dict({
        "origin": [1, 2, 3],
        "size": [4, 5, 6],
        "uv": [10, 20],
        "inflate": 0.25,
        "mirror": False,
    })
    assert cube.origin == [1.0, 2.0, 3.0]
    assert cube.uv == [10, 20]
    assert cube.inflate == 0.25

    bone = BoneDefinition.from_dict({
        "name": "testBone",
        "parent": "body",
        "pivot": [0, 10, 0],
        "cubes": [{"origin": [0, 0, 0], "size": [1, 1, 1], "uv": [0, 0]}],
    })
    assert bone.name == "testBone"
    assert len(bone.cubes) == 1

    report = ValidationReport(is_valid=True)
    report.add_issue("ERROR", "TEST_CODE", "Test failure message")
    assert not report.is_valid
    assert len(report.issues) == 1
