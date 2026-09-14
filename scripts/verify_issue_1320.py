#!/usr/bin/env python3
"""Standalone verifier for Minecraft Bedrock Humanoid NPC UV Layout (#1320).

Validates canonical 64x64 geometry definitions, non-mirrored left limb UV maps,
classic vs slim arm variants, client entity definitions, and migration logic.
"""

import json
from pathlib import Path
import sys

# Ensure root directory is on sys.path for standalone invocations
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pylint: disable=wrong-import-position
from packages.bedrock_uv_geometry import (
    ArmModelType,
    BedrockGeometry,
    BedrockHumanoidGenerator,
    BedrockUVMigrator,
    BedrockUVValidator,
    Bone,
    Cube,
    GeometryDescription,
)


def verify_models() -> bool:
    """Verify data model serialization and identity properties."""
    desc = GeometryDescription(
        identifier="geometry.test_model",
        texture_width=64,
        texture_height=64,
    )
    test_cube = Cube(
        origin=(4.0, 12.0, -2.0),
        size=(4.0, 12.0, 4.0),
        uv=(32.0, 48.0),
        mirror=False,
    )
    bone = Bone(
        name="leftArm",
        pivot=(5.0, 22.0, 0.0),
        cubes=[test_cube],
    )
    geo = BedrockGeometry(description=desc, bones=[bone])

    payload = geo.to_dict()
    valid_format = payload.get("format_version") == "1.12.0"
    reconstructed = BedrockGeometry.from_dict(payload)
    valid_reconstruction = (
        reconstructed.description.identifier == "geometry.test_model"
        and reconstructed.description.texture_width == 64
        and len(reconstructed.bones) == 1
    )
    return valid_format and valid_reconstruction


def verify_classic_geometry_file() -> bool:
    """Verify canonical models/entity/custom_npc.geo.json passes validation."""
    geo_path = ROOT_DIR / "models" / "entity" / "custom_npc.geo.json"
    if not geo_path.is_file():
        return False

    with open(geo_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    geo = BedrockGeometry.from_dict(data)
    validator = BedrockUVValidator()
    report = validator.validate_geometry(geo, expected_arm_type=ArmModelType.CLASSIC)
    if not report.is_valid:
        return False

    left_arm = geo.get_bone("leftArm")
    if not left_arm or not left_arm.cubes:
        return False

    cube = left_arm.cubes[0]
    return cube.uv == (32.0, 48.0) and cube.mirror is False and cube.size[0] == 4.0


def verify_slim_geometry_file() -> bool:
    """Verify canonical models/entity/custom_npc_slim.geo.json passes validation."""
    geo_path = ROOT_DIR / "models" / "entity" / "custom_npc_slim.geo.json"
    if not geo_path.is_file():
        return False

    with open(geo_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    geo = BedrockGeometry.from_dict(data)
    validator = BedrockUVValidator()
    report = validator.validate_geometry(geo, expected_arm_type=ArmModelType.SLIM)
    if not report.is_valid:
        return False

    left_arm = geo.get_bone("leftArm")
    right_arm = geo.get_bone("rightArm")
    if not left_arm or not right_arm or not left_arm.cubes or not right_arm.cubes:
        return False

    valid_left = left_arm.cubes[0].size[0] == 3.0 and left_arm.cubes[0].uv == (32.0, 48.0)
    valid_right = right_arm.cubes[0].size[0] == 3.0 and right_arm.cubes[0].uv == (40.0, 16.0)
    return valid_left and valid_right


def verify_entity_and_manifest() -> bool:
    """Verify entity/custom_npc.entity.json and manifest.json file declarations."""
    entity_path = ROOT_DIR / "entity" / "custom_npc.entity.json"
    manifest_path = ROOT_DIR / "manifest.json"
    if not entity_path.is_file() or not manifest_path.is_file():
        return False

    with open(entity_path, "r", encoding="utf-8") as handle:
        entity_doc = json.load(handle)
    with open(manifest_path, "r", encoding="utf-8") as handle:
        manifest_doc = json.load(handle)

    client_desc = entity_doc.get("minecraft:client_entity", {}).get("description", {})
    geos = client_desc.get("geometry", {})
    valid_entity = (
        client_desc.get("identifier") == "custom:custom_npc"
        and geos.get("default") == "geometry.custom_npc"
        and geos.get("slim") == "geometry.custom_npc.slim"
    )

    header = manifest_doc.get("header", {})
    valid_manifest = header.get("min_engine_version") == [1, 21, 50]

    return valid_entity and valid_manifest


def verify_validation_rules() -> bool:
    """Verify that validator detects invalid legacy mirrored layouts and rejects them."""
    validator = BedrockUVValidator()

    legacy_32x64 = BedrockHumanoidGenerator.generate_humanoid()
    legacy_32x64.description.texture_height = 32
    report_32x64 = validator.validate_geometry(legacy_32x64)
    if report_32x64.is_valid or not report_32x64.has_code("LEGACY_32X64_TEXTURE_DETECTED"):
        return False

    mirrored = BedrockHumanoidGenerator.generate_humanoid()
    left_arm = mirrored.get_bone("leftArm")
    if not left_arm:
        return False
    left_arm.cubes[0].mirror = True
    report_mirror = validator.validate_geometry(mirrored)
    if report_mirror.is_valid or not report_mirror.has_code("MIRRORED_LEFT_ARM_DETECTED"):
        return False

    legacy_uv = BedrockHumanoidGenerator.generate_humanoid()
    left_leg = legacy_uv.get_bone("leftLeg")
    if not left_leg:
        return False
    left_leg.cubes[0].uv = (0.0, 16.0)
    report_uv = validator.validate_geometry(legacy_uv)
    if report_uv.is_valid or not report_uv.has_code("LEGACY_LEFT_LEG_UV_DETECTED"):
        return False

    return True


def verify_generator_and_migrator() -> bool:
    """Verify programmatic generator and legacy migrator pipeline."""
    validator = BedrockUVValidator()
    classic = BedrockHumanoidGenerator.generate_humanoid(arm_type=ArmModelType.CLASSIC)
    slim = BedrockHumanoidGenerator.generate_humanoid(arm_type=ArmModelType.SLIM)

    if not validator.validate_geometry(classic, ArmModelType.CLASSIC).is_valid:
        return False
    if not validator.validate_geometry(slim, ArmModelType.SLIM).is_valid:
        return False

    migrator = BedrockUVMigrator()
    migrated_slim = migrator.migrate_geometry(classic, target_arm_type=ArmModelType.SLIM)
    return validator.validate_geometry(migrated_slim, ArmModelType.SLIM).is_valid


def main() -> int:
    """Execute all verification checks and return process exit status."""
    verifications = [
        ("Data Models & Serialization", verify_models),
        ("Classic Geometry File Integrity", verify_classic_geometry_file),
        ("Slim Geometry File Integrity", verify_slim_geometry_file),
        ("Client Entity & Manifest Declarations", verify_entity_and_manifest),
        ("Anti-Mirroring Validation Rules", verify_validation_rules),
        ("Generator & Migration Pipeline", verify_generator_and_migrator),
    ]

    all_passed = True
    for label, check_func in verifications:
        passed = check_func()
        status_str = "PASS" if passed else "FAIL"
        print(f"[{status_str}] {label}")
        if not passed:
            all_passed = False

    if all_passed:
        print("[SUCCESS] All Issue #1320 verification checks passed.")
        return 0

    print("[FAILURE] One or more verification checks failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
