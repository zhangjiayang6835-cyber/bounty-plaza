"""Test suite for Issue #1234: Custom Block Definition Schema Validation in Bedrock 1.26.30."""

import json
import sys
from pathlib import Path

try:
    from packages.bedrock_block_schema.validator import (
        BlockSchemaValidator,
        ResourcePackSoundResolver,
    )
    from packages.bedrock_block_schema.migration import MigrationPipeline
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from packages.bedrock_block_schema.validator import (
        BlockSchemaValidator,
        ResourcePackSoundResolver,
    )
    from packages.bedrock_block_schema.migration import MigrationPipeline


def test_compressed_basalt_bp_file_exists() -> None:
    """Verify that BP/blocks/compressed_basalt.json file exists on disk."""
    bp_path = Path("BP/blocks/compressed_basalt.json")
    assert bp_path.is_file(), "BP/blocks/compressed_basalt.json must exist"


def test_compressed_basalt_format_version() -> None:
    """Verify that BP/blocks/compressed_basalt.json uses format_version 1.26.30."""
    bp_path = Path("BP/blocks/compressed_basalt.json")
    with open(bp_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    assert data.get("format_version") == "1.26.30", "format_version must be 1.26.30"


def test_compressed_basalt_description_does_not_contain_sound() -> None:
    """Verify that description object strictly omits sound under format_version 1.26.30."""
    bp_path = Path("BP/blocks/compressed_basalt.json")
    with open(bp_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    desc = data.get("minecraft:block", {}).get("description", {})
    assert "sound" not in desc, "sound property is prohibited inside description in 1.26.30"
    assert desc.get("identifier") == "custom:compressed_basalt"
    assert desc.get("menu_category", {}).get("category") == "nature"


def test_compressed_basalt_components_preserved() -> None:
    """Verify that mining destruction, geometry, and material instances remain intact."""
    bp_path = Path("BP/blocks/compressed_basalt.json")
    with open(bp_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    components = data.get("minecraft:block", {}).get("components", {})
    assert "minecraft:destructible_by_mining" in components
    assert components["minecraft:destructible_by_mining"]["seconds_to_destroy"] == 2.5
    assert components.get("minecraft:geometry") == "geometry.full_block"
    materials = components.get("minecraft:material_instances", {}).get("*", {})
    assert materials.get("texture") == "compressed_basalt"
    assert materials.get("render_method") == "opaque"


def test_rp_blocks_json_mapping() -> None:
    """Verify that RP/blocks.json maps custom:compressed_basalt to stone sound."""
    rp_path = Path("RP/blocks.json")
    assert rp_path.is_file(), "RP/blocks.json must exist"

    with open(rp_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    assert "custom:compressed_basalt" in data
    entry = data["custom:compressed_basalt"]
    assert entry.get("sound") == "stone"
    assert entry.get("textures") == "compressed_basalt"


def test_rp_terrain_texture_mapping() -> None:
    """Verify that RP/terrain_texture.json configures the compressed_basalt atlas texture."""
    terrain_path = Path("RP/terrain_texture.json")
    assert terrain_path.is_file(), "RP/terrain_texture.json must exist"

    with open(terrain_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    textures = data.get("texture_data", {})
    assert "compressed_basalt" in textures
    assert textures["compressed_basalt"].get("textures") == "textures/blocks/compressed_basalt"


def test_validator_rejects_legacy_sound_in_description() -> None:
    """Ensure the schema validator flags legacy block definitions with sound in description."""
    legacy_payload = {
        "format_version": "1.26.30",
        "minecraft:block": {
            "description": {
                "identifier": "custom:legacy_block",
                "sound": "stone",
            },
            "components": {},
        },
    }
    validator = BlockSchemaValidator()
    report = validator.validate_dict(legacy_payload)

    assert not report.is_valid
    error_paths = [issue.path for issue in report.issues]
    assert "minecraft:block.description.sound" in error_paths


def test_validator_accepts_fixed_compressed_basalt() -> None:
    """Ensure the schema validator passes the compliant compressed_basalt block definition."""
    validator = BlockSchemaValidator()
    report = validator.validate_file("BP/blocks/compressed_basalt.json")

    assert report.is_valid
    assert len(report.issues) == 0
    assert report.identifier == "custom:compressed_basalt"
    assert report.format_version == "1.26.30"


def test_resource_pack_sound_resolver() -> None:
    """Ensure ResourcePackSoundResolver resolves the stone sound profile correctly."""
    resolver = ResourcePackSoundResolver("RP/blocks.json")
    report = resolver.verify_block_sound("custom:compressed_basalt", expected_sound="stone")

    assert report.is_valid
    assert resolver.resolve_sound("custom:compressed_basalt") == "stone"


def test_resource_pack_sound_resolver_missing_block() -> None:
    """Ensure ResourcePackSoundResolver flags non-existent blocks."""
    resolver = ResourcePackSoundResolver("RP/blocks.json")
    report = resolver.verify_block_sound("custom:non_existent_block", expected_sound="stone")

    assert not report.is_valid
    assert any("not defined" in issue.message for issue in report.issues)


def test_migration_pipeline_remedies_legacy_definition() -> None:
    """Ensure MigrationPipeline extracts sound from description into resource pack format."""
    legacy_block = {
        "format_version": "1.26.30",
        "minecraft:block": {
            "description": {
                "identifier": "custom:auto_fixed_block",
                "sound": "wood",
            },
            "components": {},
        },
    }
    rp_dict = {}

    updated_bp, updated_rp, modified = MigrationPipeline.migrate_block_data(legacy_block, rp_dict)

    assert modified is True
    assert "sound" not in updated_bp["minecraft:block"]["description"]
    assert updated_rp["custom:auto_fixed_block"]["sound"] == "wood"
