"""Test suite verifying Minecraft Bedrock humanoid NPC UV layout and anti-mirroring for Issue #1320."""

import json
import os
from packages.bedrock_uv_geometry.generator import BedrockHumanoidGenerator
from packages.bedrock_uv_geometry.migrator import BedrockUVMigrator
from packages.bedrock_uv_geometry.models import (
    ArmModelType,
    BedrockGeometry,
    Bone,
    Cube,
    GeometryDescription,
    ValidationSeverity,
)
from packages.bedrock_uv_geometry.validator import BedrockUVValidator


def test_canonical_classic_geometry_file_integrity() -> None:
    """Verify models/entity/custom_npc.geo.json conforms to modern Bedrock 64x64 layout."""
    filepath = os.path.join(os.getcwd(), "models", "entity", "custom_npc.geo.json")
    assert os.path.exists(filepath)

    with open(filepath, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    geometry = BedrockGeometry.from_dict(data)
    validator = BedrockUVValidator()
    report = validator.validate_geometry(geometry, expected_arm_type=ArmModelType.CLASSIC)

    assert report.is_valid is True
    assert len(report.errors()) == 0

    left_arm = geometry.get_bone("leftArm")
    assert left_arm is not None
    assert left_arm.mirror is None
    assert left_arm.cubes[0].mirror is False
    assert left_arm.cubes[0].uv == (32.0, 48.0)
    assert left_arm.cubes[0].size[0] == 4.0

    left_leg = geometry.get_bone("leftLeg")
    assert left_leg is not None
    assert left_leg.mirror is None
    assert left_leg.cubes[0].mirror is False
    assert left_leg.cubes[0].uv == (16.0, 48.0)


def test_canonical_slim_geometry_file_integrity() -> None:
    """Verify models/entity/custom_npc_slim.geo.json conforms to slim 3px arm specifications."""
    filepath = os.path.join(os.getcwd(), "models", "entity", "custom_npc_slim.geo.json")
    assert os.path.exists(filepath)

    with open(filepath, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    geometry = BedrockGeometry.from_dict(data)
    validator = BedrockUVValidator()
    report = validator.validate_geometry(geometry, expected_arm_type=ArmModelType.SLIM)

    assert report.is_valid is True
    assert len(report.errors()) == 0

    left_arm = geometry.get_bone("leftArm")
    assert left_arm is not None
    assert left_arm.cubes[0].size[0] == 3.0
    assert left_arm.cubes[0].uv == (32.0, 48.0)
    assert left_arm.pivot[1] == 21.5

    right_arm = geometry.get_bone("rightArm")
    assert right_arm is not None
    assert right_arm.cubes[0].size[0] == 3.0
    assert right_arm.pivot[1] == 21.5


def test_client_entity_json_structure() -> None:
    """Ensure client entity definition registers both classic and slim geometry identifiers."""
    filepath = os.path.join(os.getcwd(), "entity", "custom_npc.entity.json")
    assert os.path.exists(filepath)

    with open(filepath, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    client_def = data["minecraft:client_entity"]["description"]
    assert client_def["identifier"] == "custom:custom_npc"
    assert client_def["geometry"]["default"] == "geometry.custom_npc"
    assert client_def["geometry"]["slim"] == "geometry.custom_npc.slim"


def test_manifest_declares_engine_version() -> None:
    """Ensure manifest.json requires minimum engine version 1.21.50."""
    filepath = os.path.join(os.getcwd(), "manifest.json")
    assert os.path.exists(filepath)

    with open(filepath, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    assert data["header"]["min_engine_version"] == [1, 21, 50]


def test_legacy_mirror_cube_detection() -> None:
    """Verify validator detects and rejects cubes marked with legacy mirror:true."""
    geo = BedrockHumanoidGenerator.generate_humanoid()
    left_arm = geo.get_bone("leftArm")
    assert left_arm is not None
    left_arm.cubes[0].mirror = True

    validator = BedrockUVValidator()
    report = validator.validate_geometry(geo)

    assert report.is_valid is False
    assert report.has_code("MIRRORED_LEFT_ARM_DETECTED")


def test_legacy_mirror_bone_detection() -> None:
    """Verify validator detects legacy mirror flag on bone level."""
    geo = BedrockHumanoidGenerator.generate_humanoid()
    left_leg = geo.get_bone("leftLeg")
    assert left_leg is not None
    left_leg.mirror = True

    validator = BedrockUVValidator()
    report = validator.validate_geometry(geo)

    assert report.is_valid is False
    assert report.has_code("MIRRORED_LEFT_LEG_DETECTED")


def test_legacy_uv_reuse_detection() -> None:
    """Detect left arm referencing legacy right arm UV offset [40, 16]."""
    geo = BedrockHumanoidGenerator.generate_humanoid()
    left_arm = geo.get_bone("leftArm")
    assert left_arm is not None
    left_arm.cubes[0].uv = (40.0, 16.0)

    validator = BedrockUVValidator()
    report = validator.validate_geometry(geo)

    assert report.is_valid is False
    assert report.has_code("LEGACY_LEFT_ARM_UV_DETECTED")


def test_legacy_32x64_texture_detection() -> None:
    """Detect legacy 64x32 texture dimensions."""
    geo = BedrockHumanoidGenerator.generate_humanoid()
    geo.description.texture_height = 32

    validator = BedrockUVValidator()
    report = validator.validate_geometry(geo)

    assert report.is_valid is False
    assert report.has_code("LEGACY_32X64_TEXTURE_DETECTED")


def test_arm_dimension_mismatch_detection() -> None:
    """Detect width mismatch between classic 4px arm and slim expectation."""
    geo = BedrockHumanoidGenerator.generate_humanoid(arm_type=ArmModelType.CLASSIC)
    validator = BedrockUVValidator()
    report = validator.validate_geometry(geo, expected_arm_type=ArmModelType.SLIM)

    assert report.is_valid is False
    assert report.has_code("ARM_DIMENSION_MISMATCH")


def test_uv_out_of_bounds_detection() -> None:
    """Detect cube UV rectangles exceeding 64x64 texture boundaries."""
    geo = BedrockHumanoidGenerator.generate_humanoid()
    body = geo.get_bone("body")
    assert body is not None
    body.cubes[0].uv = (60.0, 60.0)

    validator = BedrockUVValidator()
    report = validator.validate_geometry(geo)

    assert report.is_valid is False
    assert report.has_code("UV_OUT_OF_BOUNDS")


def test_per_face_uv_out_of_bounds_detection() -> None:
    """Detect per-face UV maps exceeding texture boundaries."""
    geo = BedrockHumanoidGenerator.generate_humanoid()
    head = geo.get_bone("head")
    assert head is not None
    head.cubes[0].uv = {
        "north": {"uv": [60.0, 60.0], "uv_size": [10.0, 10.0]}
    }

    validator = BedrockUVValidator()
    report = validator.validate_geometry(geo)

    assert report.is_valid is False
    assert report.has_code("PER_FACE_UV_OUT_OF_BOUNDS")


def test_orphaned_parent_bone_detection() -> None:
    """Detect bones referencing undefined parents."""
    geo = BedrockHumanoidGenerator.generate_humanoid()
    geo.bones.append(Bone(name="floating_wing", parent="non_existent_spine"))

    validator = BedrockUVValidator()
    report = validator.validate_geometry(geo)

    assert report.is_valid is False
    assert report.has_code("ORPHANED_BONE_PARENT")


def test_migrator_converts_legacy_geometry_to_modern() -> None:
    """Verify migrator corrects legacy mirrored UVs to modern 64x64 unmirrored layout."""
    legacy_desc = GeometryDescription(
        identifier="geometry.legacy_npc",
        texture_width=64,
        texture_height=32,
    )
    legacy_bones = [
        Bone(name="root", pivot=(0.0, 0.0, 0.0)),
        Bone(name="waist", parent="root", pivot=(0.0, 12.0, 0.0)),
        Bone(
            name="body",
            parent="waist",
            pivot=(0.0, 24.0, 0.0),
            cubes=[Cube(origin=(-4.0, 12.0, -2.0), size=(8.0, 12.0, 4.0), uv=(16.0, 16.0))],
        ),
        Bone(
            name="head",
            parent="body",
            pivot=(0.0, 24.0, 0.0),
            cubes=[Cube(origin=(-4.0, 24.0, -4.0), size=(8.0, 8.0, 8.0), uv=(0.0, 0.0))],
        ),
        Bone(
            name="rightArm",
            parent="body",
            pivot=(-5.0, 22.0, 0.0),
            cubes=[Cube(origin=(-8.0, 12.0, -2.0), size=(4.0, 12.0, 4.0), uv=(40.0, 16.0))],
        ),
        Bone(
            name="leftArm",
            parent="body",
            pivot=(5.0, 22.0, 0.0),
            mirror=True,
            cubes=[Cube(origin=(4.0, 12.0, -2.0), size=(4.0, 12.0, 4.0), uv=(40.0, 16.0), mirror=True)],
        ),
        Bone(
            name="rightLeg",
            parent="root",
            pivot=(-1.9, 12.0, 0.0),
            cubes=[Cube(origin=(-3.9, 0.0, -2.0), size=(4.0, 12.0, 4.0), uv=(0.0, 16.0))],
        ),
        Bone(
            name="leftLeg",
            parent="root",
            pivot=(1.9, 12.0, 0.0),
            mirror=True,
            cubes=[Cube(origin=(-0.1, 0.0, -2.0), size=(4.0, 12.0, 4.0), uv=(0.0, 16.0), mirror=True)],
        ),
    ]
    legacy_geo = BedrockGeometry(description=legacy_desc, bones=legacy_bones)

    validator = BedrockUVValidator()
    initial_report = validator.validate_geometry(legacy_geo)
    assert initial_report.is_valid is False
    assert initial_report.has_code("LEGACY_32X64_TEXTURE_DETECTED")
    assert initial_report.has_code("MIRRORED_LEFT_ARM_DETECTED")
    assert initial_report.has_code("LEGACY_LEFT_ARM_UV_DETECTED")

    migrator = BedrockUVMigrator()
    migrated_geo = migrator.migrate_geometry(
        legacy_geo,
        target_arm_type=ArmModelType.SLIM,
        new_identifier="geometry.migrated_npc.slim",
    )

    migrated_report = validator.validate_geometry(migrated_geo, expected_arm_type=ArmModelType.SLIM)
    assert migrated_report.is_valid is True
    assert len(migrated_report.errors()) == 0

    assert migrated_geo.description.texture_width == 64
    assert migrated_geo.description.texture_height == 64
    assert migrated_geo.description.identifier == "geometry.migrated_npc.slim"

    migrated_left_arm = migrated_geo.get_bone("leftArm")
    assert migrated_left_arm is not None
    assert migrated_left_arm.mirror is None
    assert migrated_left_arm.cubes[0].mirror is False
    assert migrated_left_arm.cubes[0].uv == (32.0, 48.0)
    assert migrated_left_arm.cubes[0].size[0] == 3.0


def test_roundtrip_geometry_serialization() -> None:
    """Verify geometry serialization to dict and parsing back is lossless."""
    original = BedrockHumanoidGenerator.generate_humanoid("geometry.roundtrip_test", ArmModelType.SLIM)
    serialized = original.to_dict()
    reconstructed = BedrockGeometry.from_dict(serialized)

    assert reconstructed.description.identifier == "geometry.roundtrip_test"
    assert reconstructed.description.texture_width == 64
    assert reconstructed.description.texture_height == 64
    assert len(reconstructed.bones) == len(original.bones)

    validator = BedrockUVValidator()
    report = validator.validate_geometry(reconstructed, ArmModelType.SLIM)
    assert report.is_valid is True
