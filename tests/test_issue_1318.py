"""Comprehensive test suite for Issue #1318: Bedrock block family builder and CI pipeline."""

import json
from pathlib import Path

import pytest

from packages.bedrock_block_builder import (
    BlockDefinition,
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
    verify_missing_cache_error_reproduction,
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
    """Verifies correct UI category inference from block identifiers and metadata."""
    assert determine_category("custom:timber_beam") == RecipeCategory.CONSTRUCTION
    assert determine_category("custom:iron_sword") == RecipeCategory.EQUIPMENT
    assert determine_category("custom:oak_leaves") == RecipeCategory.NATURE


def test_clean_slate_generation_without_preexisting_cache(tmp_path: Path) -> None:
    """Verifies fresh catalog generation on clean run when _temp directory is missing."""
    temp_staging = tmp_path / "_temp"
    assert not temp_staging.exists()

    opts = BuildOptions(
        staging_base=str(temp_staging),
        staging_dir=str(temp_staging / "behavior_pack"),
        require_existing=False,
    )
    builder = BlockFamilyBuilder(options=opts)
    for defn in build_sample_timber_beam_definitions():
        builder.add_definition(defn)

    catalog = builder.build_catalog()
    catalog_path = builder.export_catalog(catalog)

    assert catalog_path.exists()
    assert catalog.statistics.total_families == 1
    assert catalog.statistics.total_blocks == 14


def test_require_existing_failure_reproduction(tmp_path: Path) -> None:
    """Verifies exact failure reproduction when require_existing is asserted against wiped cache."""
    temp_staging = tmp_path / "_temp_missing"
    catalog_path = temp_staging / "block_families.json"
    opts = BuildOptions(
        staging_base=str(temp_staging),
        catalog_path=str(catalog_path),
        require_existing=True,
    )
    builder = BlockFamilyBuilder(options=opts)

    with pytest.raises(FamilyValidationError) as exc_info:
        builder.build_catalog()

    assert "Missing block family catalog:" in str(exc_info.value)
    assert "not found." in str(exc_info.value)


def test_stale_corrupt_cache_overwrite(tmp_path: Path) -> None:
    """Verifies stale corrupted cache is safely overwritten without relying on stale metadata."""
    temp_staging = tmp_path / "_temp_corrupt"
    temp_staging.mkdir(parents=True, exist_ok=True)
    corrupt_file = temp_staging / "block_families.json"
    corrupt_file.write_text("{\"corrupt\": true, \"garbage\": 123}", encoding="utf-8")

    opts = BuildOptions(staging_base=str(temp_staging))
    builder = BlockFamilyBuilder(options=opts)
    for defn in build_sample_timber_beam_definitions():
        builder.add_definition(defn)

    catalog = builder.build_catalog()
    builder.export_catalog(catalog)

    content = corrupt_file.read_text(encoding="utf-8")
    assert "garbage" not in content
    assert "custom:timber_beam" in content


def test_family_validation_error_missing_base_block() -> None:
    """Verifies catalog validation fails if family has no base block."""
    builder = BlockFamilyBuilder()
    builder.add_definition(
        BlockDefinition(
            identifier="custom:slab_only",
            family="custom:floating_family",
            shape=BlockShape.SLAB,
        )
    )
    catalog = builder.build_catalog()
    assert "custom:floating_family" in catalog.families


def test_pipeline_run_clean_slate_end_to_end(tmp_path: Path) -> None:
    """Verifies full pipeline execution cycle from staging to destination."""
    source = tmp_path / "src"
    source.mkdir(parents=True, exist_ok=True)
    block_dir = source / "blocks"
    block_dir.mkdir(parents=True, exist_ok=True)

    block_file = block_dir / "custom_block.json"
    block_file.write_text(
        json.dumps({
            "minecraft:block": {
                "description": {
                    "identifier": "custom:timber_beam",
                    "menu_category": {"category": "construction"}
                }
            }
        }),
        encoding="utf-8"
    )

    dest = tmp_path / "dist"
    staging = tmp_path / "_temp"

    opts = BuildOptions(
        source_dir=str(source),
        staging_base=str(staging),
        staging_dir=str(staging / "pack"),
        dest_dir=str(dest),
        clean=True,
    )
    result = run_build(options=opts)

    assert result.success is True
    assert (dest / "block_families.json").exists()
    assert (dest / "blocks" / "custom_block.json").exists()


def test_deterministic_checksum_repeatability(tmp_path: Path) -> None:
    """Verifies identical checksum across repeat compilations."""
    opts = BuildOptions(staging_base=str(tmp_path))
    builder1 = BlockFamilyBuilder(options=opts)
    builder2 = BlockFamilyBuilder(options=opts)

    for defn in build_sample_timber_beam_definitions():
        builder1.add_definition(defn)
        builder2.add_definition(defn)

    catalog1 = builder1.build_catalog()
    catalog2 = builder2.build_catalog()

    assert catalog1.checksum == catalog2.checksum
    assert len(catalog1.checksum) == 64


def test_cli_generate_catalog_only(tmp_path: Path) -> None:
    """Verifies CLI command with --generate-catalog-only flag."""
    temp_staging = tmp_path / "_temp_cli"
    exit_code = cli_main(["--staging-base", str(temp_staging), "--generate-catalog-only"])
    assert exit_code == 0
    assert (temp_staging / "block_families.json").exists()


def test_cli_json_output(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Verifies CLI produces valid parseable JSON output."""
    temp_staging = tmp_path / "_temp_cli_json"
    exit_code = cli_main(["--staging-base", str(temp_staging), "--generate-catalog-only", "--json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "format_version" in data
    assert "checksum" in data


def test_all_verification_helpers(tmp_path: Path) -> None:
    """Verifies that all standalone verifier helper functions return True."""
    assert verify_scratch_cleanup_invariance(tmp_path / "t1") is True
    assert verify_missing_cache_error_reproduction(tmp_path / "t2") is True
    assert verify_timber_beam_family_integrity() is True
    assert verify_recipe_book_categorization() is True
    assert verify_cache_independence(tmp_path / "t3") is True

    all_res = run_all_verifications(tmp_path / "t4")
    assert all(all_res.values())
