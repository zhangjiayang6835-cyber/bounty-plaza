#!/usr/bin/env python3
"""Standalone verifier for Bedrock Custom Block Schema (#1326).

Validates custom block JSON definitions, directional material instances,
isotropic face rotations, supporting resource pack assets, and automated migration logic.
"""

import json
from pathlib import Path
import sys

from packages.bedrock_block_validator import (
    BedrockBlockDefinition,
    BedrockBlockGenerator,
    BedrockBlockMigrator,
    BedrockBlockSchemaValidator,
    BlockComponents,
    BlockDescription,
    MaterialInstance,
    RenderMethod,
)

ROOT_DIR = Path(__file__).resolve().parent.parent




def verify_models() -> bool:
    """Verify data model serialization and identity properties."""
    instance = MaterialInstance(
        texture="compressed_basalt_top",
        render_method=RenderMethod.OPAQUE,
        face_dimming=True,
        ambient_occlusion=1.0,
        isotropic=True,
    )
    definition = BedrockBlockDefinition(
        format_version="1.21.50",
        description=BlockDescription(identifier="custom:compressed_basalt"),
        components=BlockComponents(
            material_instances={"up": instance},
        ),
    )

    data = definition.to_dict()
    valid_format = data.get("format_version") == "1.21.50"
    valid_identifier = (
        data.get("minecraft:block", {})
        .get("description", {})
        .get("identifier")
        == "custom:compressed_basalt"
    )
    up_inst = (
        data.get("minecraft:block", {})
        .get("components", {})
        .get("minecraft:material_instances", {})
        .get("up", {})
    )
    valid_instance = (
        up_inst.get("render_method") == "opaque"
        and up_inst.get("isotropic") is True
    )

    return valid_format and valid_identifier and valid_instance


def verify_schema_validation_rules() -> bool:
    """Validate schema constraints rejecting wildcard alpha_test and misplaced isotropic."""
    broken_wildcard = {
        "format_version": "1.21.40",
        "minecraft:block": {
            "description": {"identifier": "custom:compressed_basalt"},
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
    report1 = BedrockBlockSchemaValidator.validate_json_dict(broken_wildcard)
    if report1.is_valid or not report1.has_code("INVALID_WILDCARD_ALPHA_TEST"):
        return False

    misplaced_isotropic = {
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
    report2 = BedrockBlockSchemaValidator.validate_json_dict(misplaced_isotropic)
    if report2.is_valid or not report2.has_code("ISOTROPIC_IN_DESCRIPTION"):
        return False

    return True


def verify_compressed_basalt_definition() -> bool:
    """Verify physical blocks/compressed_basalt.json file passes schema validation."""
    block_path = ROOT_DIR / "blocks" / "compressed_basalt.json"
    if not block_path.is_file():
        return False

    report = BedrockBlockSchemaValidator.validate_file(block_path)
    if not report.is_valid:
        return False

    with open(block_path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)

    mat_instances = (
        doc.get("minecraft:block", {})
        .get("components", {})
        .get("minecraft:material_instances", {})
    )
    up_face = mat_instances.get("up", {})
    down_face = mat_instances.get("down", {})

    has_up_isotropic = up_face.get("isotropic") is True
    has_down_isotropic = down_face.get("isotropic") is True
    valid_up_render = up_face.get("render_method") == "opaque"
    valid_wildcard_render = mat_instances.get("*", {}).get("render_method") == "opaque"

    return (
        has_up_isotropic
        and has_down_isotropic
        and valid_up_render
        and valid_wildcard_render
    )


def verify_generator_and_migrator() -> bool:
    """Verify programmatic generator and legacy migrator output validity."""
    generated = BedrockBlockGenerator.create_compressed_basalt_dict()
    gen_report = BedrockBlockSchemaValidator.validate_compressed_basalt_dict(generated)
    if not gen_report.is_valid:
        return False

    legacy_def = {
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

    migrated = BedrockBlockMigrator.migrate_definition(legacy_def)
    mig_report = BedrockBlockSchemaValidator.validate_compressed_basalt_dict(migrated)
    return mig_report.is_valid


def verify_supporting_assets() -> bool:
    """Verify supporting culling, geometry model, and terrain texture atlas."""
    culling_path = ROOT_DIR / "block_culling" / "compressed_basalt.culling.json"
    geo_path = ROOT_DIR / "models" / "blocks" / "compressed_basalt.geo.json"
    texture_path = ROOT_DIR / "textures" / "terrain_texture.json"
    manifest_path = ROOT_DIR / "manifest.json"

    files = [culling_path, geo_path, texture_path, manifest_path]
    for file_path in files:
        if not file_path.is_file():
            return False

    with open(texture_path, "r", encoding="utf-8") as fh:
        atlas = json.load(fh)
    textures = atlas.get("texture_data", {})
    has_textures = (
        "compressed_basalt_top" in textures
        and "compressed_basalt_bottom" in textures
        and "compressed_basalt_side" in textures
    )

    return has_textures


def main() -> int:
    """Run all verification checks and return process exit status."""
    verifications = [
        ("Data Models & Serialization", verify_models),
        ("Schema Validation Rules", verify_schema_validation_rules),
        ("Compressed Basalt Block Definition", verify_compressed_basalt_definition),
        ("Generator & Migration Pipeline", verify_generator_and_migrator),
        ("Supporting Assets & Manifest", verify_supporting_assets),
    ]

    all_passed = True
    for label, check_func in verifications:
        passed = check_func()
        status_str = "PASS" if passed else "FAIL"
        print(f"[{status_str}] {label}")
        if not passed:
            all_passed = False

    if all_passed:
        print("[SUCCESS] All Issue #1326 verification checks passed.")
        return 0

    print("[FAILURE] One or more verification checks failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
