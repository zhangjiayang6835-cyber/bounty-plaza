"""Standalone verification script for Issue #1228 acceptance criteria."""

import json
import sys
from pathlib import Path

try:
    from packages.bedrock_humanoid_npc.migration import EntityMigrationPipeline
    from packages.bedrock_humanoid_npc.validator import (
        GeometryModelAnalyzer,
        HumanoidEntityValidator,
    )
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from packages.bedrock_humanoid_npc.migration import EntityMigrationPipeline
    from packages.bedrock_humanoid_npc.validator import (
        GeometryModelAnalyzer,
        HumanoidEntityValidator,
    )

ROOT_DIR = Path(__file__).resolve().parent.parent


def verify_client_entity_definition() -> bool:
    """Verify that RP/entity/custom_npc.entity.json uses modern humanoid geometry."""
    entity_path = ROOT_DIR / "RP" / "entity" / "custom_npc.entity.json"
    if not entity_path.is_file():
        print("FAIL: RP/entity/custom_npc.entity.json does not exist")
        return False

    with open(entity_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    validator = HumanoidEntityValidator()
    report = validator.validate_entity_dict(data, source_path=str(entity_path))

    if not report.is_valid:
        print(f"FAIL: Entity validation failed with {len(report.issues)} issues:")
        for issue in report.issues:
            print(f"  - [{issue.severity}] {issue.code}: {issue.message}")
        return False

    desc = data.get("minecraft:client_entity", {}).get("description", {})
    geo = desc.get("geometry", {}).get("default", "")
    if geo != "geometry.humanoid.custom":
        print(f"FAIL: Expected geometry.humanoid.custom, got '{geo}'")
        return False

    controllers = desc.get("render_controllers", [])
    if "controller.render.default" not in controllers:
        print(f"FAIL: Expected controller.render.default, got {controllers}")
        return False

    print("PASS: RP/entity/custom_npc.entity.json is fully compliant")
    return True


def verify_geometry_model() -> bool:
    """Verify that RP/models/entity/custom_npc.geo.json supports asymmetric dual layers."""
    geo_path = ROOT_DIR / "RP" / "models" / "entity" / "custom_npc.geo.json"
    if not geo_path.is_file():
        print("FAIL: RP/models/entity/custom_npc.geo.json does not exist")
        return False

    with open(geo_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    analyzer = GeometryModelAnalyzer()
    report = analyzer.analyze_geometry_dict(data, source_path=str(geo_path))

    if not report.is_valid:
        print(f"FAIL: Geometry analysis failed with {len(report.issues)} issues:")
        for issue in report.issues:
            print(f"  - [{issue.severity}] {issue.code}: {issue.message}")
        return False

    if not report.asymmetric_limbs_supported:
        print("FAIL: Asymmetric limbs not verified in geometry")
        return False

    if not report.dual_layer_supported:
        print("FAIL: Dual layer outer geometry not verified")
        return False

    print("PASS: Geometry model verifies 64x64 asymmetric limbs and dual layers")
    return True


def verify_legacy_migration() -> bool:
    """Verify that EntityMigrationPipeline transforms legacy zombie definition."""
    legacy_sample = {
        "format_version": "1.8.0",
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

    pipeline = EntityMigrationPipeline()
    migrated = pipeline.migrate_entity_definition(legacy_sample)

    validator = HumanoidEntityValidator()
    report = validator.validate_entity_dict(migrated)

    if not report.is_valid:
        print("FAIL: Migrated entity failed validation")
        return False

    print("PASS: Legacy entity definition successfully migrated and validated")
    return True


def main() -> int:
    """Execute all acceptance verification routines for Issue #1228."""
    print("Executing Issue #1228 Acceptance Verification...")
    entity_ok = verify_client_entity_definition()
    geo_ok = verify_geometry_model()
    migration_ok = verify_legacy_migration()

    if entity_ok and geo_ok and migration_ok:
        print("All Issue #1228 acceptance checks PASSED.")
        return 0

    print("Issue #1228 acceptance verification FAILED.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
