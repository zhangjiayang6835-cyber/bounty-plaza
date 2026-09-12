"""Comprehensive test suite for Issue #1227: Bedrock block family builder and CI pipeline."""

import json
from pathlib import Path

import pytest

from packages.bedrock_block_builder import (
    BlockFamilyBuilder,
    BlockShape,
    BuildOptions,
    FamilyValidationError,
    RecipeCategory,
    determine_category,
    determine_family,
    determine_shape,
    run_build,
)
from packages.bedrock_block_builder.cli import main as cli_main
from packages.bedrock_block_builder.verifier import (
    build_sample_timber_beam_definitions,
    run_all_verifications,
    verify_cache_independence,
    verify_recipe_book_categorization,
    verify_scratch_cleanup_invariance,
    verify_timber_beam_family_integrity,
)


def test_determine_shape_all_fourteen_variants() -> None:
    """Verifies shape classification across all 14 structural variants."""
    expected_mappings = [
        ("custom:timber_beam", BlockShape.BASE),
        ("custom:timber_beam_slab", BlockShape.SLAB),
        ("custom:timber_beam_double_slab", BlockShape.DOUBLE_SLAB),
        ("custom:timber_beam_stair", BlockShape.STAIR),
        ("custom:timber_beam_vertical", BlockShape.VERTICAL),
        ("custom:timber_beam_horizontal", BlockShape.HORIZONTAL),
        ("custom:timber_beam_stripped", BlockShape.STRIPPED),
        ("custom:timber_beam_corner", BlockShape.CORNER),
        ("custom:timber_beam_pillar", BlockShape.PILLAR),
        ("custom:timber_beam_post", BlockShape.POST),
        ("custom:timber_beam_wall", BlockShape.WALL),
        ("custom:timber_beam_fence", BlockShape.FENCE),
        ("custom:timber_beam_fence_gate", BlockShape.FENCE_GATE),
        ("custom:timber_beam_carved", BlockShape.CARVED),
    ]
    for identifier, expected_shape in expected_mappings:
        assert determine_shape(identifier) == expected_shape


def test_determine_family_strips_suffixes() -> None:
    """Verifies that all 14 variants resolve to the custom:timber_beam root family."""
    variants = [
        "custom:timber_beam",
        "custom:timber_beam_slab",
        "custom:timber_beam_double_slab",
        "custom:timber_beam_stair",
        "custom:timber_beam_vertical",
        "custom:timber_beam_horizontal",
        "custom:timber_beam_stripped",
        "custom:timber_beam_corner",
        "custom:timber_beam_pillar",
        "custom:timber_beam_post",
        "custom:timber_beam_wall",
        "custom:timber_beam_fence",
        "custom:timber_beam_fence_gate",
        "custom:timber_beam_carved",
    ]
    for identifier in variants:
        assert determine_family(identifier) == "custom:timber_beam"


def test_determine_category_inference() -> None:
    """Verifies recipe book UI category determination."""
    assert determine_category("custom:timber_beam") == RecipeCategory.CONSTRUCTION
    assert determine_category("custom:diamond_sword") == RecipeCategory.EQUIPMENT
    assert determine_category("custom:oak_sapling") == RecipeCategory.NATURE


def test_require_existing_reproduces_issue_failure(tmp_path: Path) -> None:
    """Verifies that require_existing=True fails when scratch folders were wiped."""
    missing_catalog = tmp_path / "_temp" / "block_families.json"
    opts = BuildOptions(
        staging_base=str(tmp_path / "_temp"),
        catalog_path=str(missing_catalog),
        require_existing=True,
    )
    builder = BlockFamilyBuilder(options=opts)
    for defn in build_sample_timber_beam_definitions():
        builder.add_definition(defn)

    with pytest.raises(FamilyValidationError) as excinfo:
        builder.build_catalog()

    assert "Missing block family catalog" in str(excinfo.value)


def test_clean_slate_generation_succeeds_without_cache(tmp_path: Path) -> None:
    """Verifies that dynamic compilation creates catalog cleanly when _temp is wiped."""
    scratch_dir = tmp_path / "_temp"
    catalog_file = scratch_dir / "block_families.json"
    assert not scratch_dir.exists()

    opts = BuildOptions(
        staging_base=str(scratch_dir),
        catalog_path=str(catalog_file),
        require_existing=False,
    )
    builder = BlockFamilyBuilder(options=opts)
    for defn in build_sample_timber_beam_definitions():
        builder.add_definition(defn)

    catalog = builder.build_catalog()
    exported = builder.export_catalog(catalog)

    assert exported.exists()
    assert catalog.statistics.total_families == 1
    assert catalog.statistics.total_blocks == 14
    assert catalog.families["custom:timber_beam"].base_block == "custom:timber_beam"
    assert len(catalog.families["custom:timber_beam"].members) == 14


def test_recipe_book_ui_categorization_zero_missing() -> None:
    """Verifies that all 14 block definitions are properly categorized in recipe book UI."""
    builder = BlockFamilyBuilder()
    for defn in build_sample_timber_beam_definitions():
        builder.add_definition(defn)

    catalog = builder.build_catalog()
    cat_members = catalog.recipe_categories.get("construction", [])
    assert len(cat_members) == 14
    for defn in build_sample_timber_beam_definitions():
        assert defn.identifier in cat_members


def test_cache_overwriting_stale_data(tmp_path: Path) -> None:
    """Verifies that stale or corrupt cache is cleanly replaced."""
    assert verify_cache_independence(tmp_path)


def test_deterministic_checksums() -> None:
    """Verifies that repeated compilation produces identical SHA-256 checksums."""
    builder_a = BlockFamilyBuilder()
    for defn in build_sample_timber_beam_definitions():
        builder_a.add_definition(defn)
    cat_a = builder_a.build_catalog()

    builder_b = BlockFamilyBuilder()
    for defn in reversed(build_sample_timber_beam_definitions()):
        builder_b.add_definition(defn)
    cat_b = builder_b.build_catalog()

    assert cat_a.checksum == cat_b.checksum
    assert len(cat_a.checksum) == 64


def test_parse_real_json_block_files(tmp_path: Path) -> None:
    """Verifies reading real Bedrock JSON files from disk."""
    pack_dir = tmp_path / "blocks"
    pack_dir.mkdir(parents=True)

    block_data = {
        "format_version": "1.20.80",
        "minecraft:block": {
            "description": {
                "identifier": "custom:timber_beam_stair",
                "menu_category": {"category": "construction", "group": "itemGroup.name.wood"},
            },
            "components": {
                "minecraft:geometry": "geometry.stair",
            },
        },
    }
    block_file = pack_dir / "timber_beam_stair.json"
    with open(block_file, "w", encoding="utf-8") as handle:
        json.dump(block_data, handle)

    builder = BlockFamilyBuilder()
    parsed = builder.parse_block_file(block_file)
    assert parsed is not None
    assert parsed.identifier == "custom:timber_beam_stair"
    assert parsed.family == "custom:timber_beam"
    assert parsed.shape == BlockShape.STAIR
    assert parsed.category == RecipeCategory.CONSTRUCTION


def test_bedrock_build_pipeline_clean_slate_run(tmp_path: Path) -> None:
    """Verifies end-to-end clean-slate build pipeline execution."""
    src_dir = tmp_path / "packs" / "behavior_pack"
    blocks_dir = src_dir / "blocks"
    blocks_dir.mkdir(parents=True)

    for defn in build_sample_timber_beam_definitions():
        sample_json = {
            "format_version": "1.20.80",
            "minecraft:block": {
                "description": {
                    "identifier": defn.identifier,
                    "menu_category": {"category": "construction", "group": defn.group},
                }
            },
        }
        filename = defn.identifier.replace("custom:", "") + ".json"
        with open(blocks_dir / filename, "w", encoding="utf-8") as handle:
            json.dump(sample_json, handle)

    staging_base = tmp_path / "_temp"
    staging_dir = staging_base / "behavior_pack"
    dest_dir = tmp_path / "dist" / "behavior_pack"

    opts = BuildOptions(
        source_dir=str(src_dir),
        staging_base=str(staging_base),
        staging_dir=str(staging_dir),
        dest_dir=str(dest_dir),
        clean=True,
    )

    result = run_build(options=opts)
    assert result.success is True
    assert result.catalog is not None
    assert result.catalog.statistics.total_blocks == 14
    assert (dest_dir / "block_families.json").exists()
    assert (dest_dir / "blocks" / "timber_beam.json").exists()


def test_validator_detects_undefined_family_reference() -> None:
    """Verifies that validation flags undefined references."""
    builder = BlockFamilyBuilder(fail_on_missing=False)
    for defn in build_sample_timber_beam_definitions():
        builder.add_definition(defn)

    catalog = builder.build_catalog()
    catalog.families["custom:timber_beam"].members["ghost_shape"] = "custom:ghost_block"

    errors = builder.validate_catalog(catalog)
    assert len(errors) > 0
    assert any("custom:ghost_block" in err for err in errors)


def test_cli_main_clean_build(tmp_path: Path) -> None:
    """Verifies CLI execution with clean build flags."""
    src_dir = tmp_path / "packs" / "behavior_pack"
    blocks_dir = src_dir / "blocks"
    blocks_dir.mkdir(parents=True)

    sample_json = {
        "format_version": "1.20.80",
        "minecraft:block": {
            "description": {
                "identifier": "custom:timber_beam",
                "menu_category": {"category": "construction"},
            }
        },
    }
    with open(blocks_dir / "timber_beam.json", "w", encoding="utf-8") as handle:
        json.dump(sample_json, handle)

    args = [
        "--source",
        str(src_dir),
        "--staging-base",
        str(tmp_path / "_temp"),
        "--staging",
        str(tmp_path / "_temp" / "behavior_pack"),
        "--dest",
        str(tmp_path / "dist" / "behavior_pack"),
        "--clean",
        "--json",
    ]
    exit_code = cli_main(args)
    assert exit_code == 0


def test_all_verifications_module(tmp_path: Path) -> None:
    """Verifies that all verification helper functions in verifier.py pass."""
    assert verify_scratch_cleanup_invariance(tmp_path) is True
    assert verify_timber_beam_family_integrity() is True
    assert verify_recipe_book_categorization() is True
    results = run_all_verifications(tmp_path)
    assert all(results.values())
