"""Verification engine proving build pipeline invariance and registry integrity."""

import shutil
from pathlib import Path

from packages.bedrock_block_builder.builder import BlockFamilyBuilder
from packages.bedrock_block_builder.models import (
    BlockDefinition,
    BlockShape,
    BuildOptions,
    RecipeCategory,
)


def build_sample_timber_beam_definitions() -> list[BlockDefinition]:
    """Generates the full canonical 14-member timber beam block definition set."""
    members = [
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
    return [
        BlockDefinition(
            identifier=ident,
            family="custom:timber_beam",
            shape=shape,
            category=RecipeCategory.CONSTRUCTION,
            group="itemGroup.name.wood",
        )
        for ident, shape in members
    ]


def verify_scratch_cleanup_invariance(temp_base: Path) -> bool:
    """Verifies that wiping scratch folders does not break block family compilation."""
    staging_base = temp_base / "_temp"
    staging_dir = staging_base / "behavior_pack"

    opts = BuildOptions(
        staging_base=str(staging_base),
        staging_dir=str(staging_dir),
    )
    builder = BlockFamilyBuilder(options=opts)
    for defn in build_sample_timber_beam_definitions():
        builder.add_definition(defn)

    catalog = builder.build_catalog()
    builder.export_catalog(catalog)

    if staging_base.exists():
        shutil.rmtree(staging_base, ignore_errors=True)

    fresh_builder = BlockFamilyBuilder(options=opts)
    for defn in build_sample_timber_beam_definitions():
        fresh_builder.add_definition(defn)

    fresh_catalog = fresh_builder.build_catalog()
    fresh_builder.export_catalog(fresh_catalog)

    return (
        fresh_catalog.statistics.total_families == 1
        and fresh_catalog.statistics.total_blocks == 14
        and (staging_base / "block_families.json").exists()
    )


def verify_timber_beam_family_integrity() -> bool:
    """Verifies that all 14 timber beam variants are categorized under custom:timber_beam."""
    builder = BlockFamilyBuilder()
    for defn in build_sample_timber_beam_definitions():
        builder.add_definition(defn)

    catalog = builder.build_catalog()
    family = catalog.families.get("custom:timber_beam")
    if not family:
        return False

    if len(family.members) != 14:
        return False

    for defn in build_sample_timber_beam_definitions():
        if catalog.block_to_family.get(defn.identifier) != "custom:timber_beam":
            return False

    return True


def verify_recipe_book_categorization() -> bool:
    """Verifies that all 14 timber beam block definitions exist in construction category."""
    builder = BlockFamilyBuilder()
    for defn in build_sample_timber_beam_definitions():
        builder.add_definition(defn)

    catalog = builder.build_catalog()
    construction_blocks = catalog.recipe_categories.get(RecipeCategory.CONSTRUCTION.value, [])

    if len(construction_blocks) != 14:
        return False

    for defn in build_sample_timber_beam_definitions():
        if defn.identifier not in construction_blocks:
            return False

    return True


def verify_cache_independence(temp_base: Path) -> bool:
    """Verifies that stale cache files are cleanly overwritten without persistence."""
    staging_base = temp_base / "_temp_corrupt"
    staging_base.mkdir(parents=True, exist_ok=True)
    stale_file = staging_base / "block_families.json"
    stale_file.write_text('{"stale": true, "invalid": "corrupt"}', encoding="utf-8")

    opts = BuildOptions(staging_base=str(staging_base))
    builder = BlockFamilyBuilder(options=opts)
    for defn in build_sample_timber_beam_definitions():
        builder.add_definition(defn)

    catalog = builder.build_catalog()
    builder.export_catalog(catalog)

    reloaded_text = stale_file.read_text(encoding="utf-8")
    return (
        '"stale"' not in reloaded_text
        and catalog.statistics.total_blocks == 14
        and catalog.statistics.total_families == 1
    )


def run_all_verifications(temp_base: Path) -> dict[str, bool]:
    """Runs the complete suite of verification checks and returns status report."""
    return {
        "scratch_cleanup_invariance": verify_scratch_cleanup_invariance(temp_base),
        "timber_beam_family_integrity": verify_timber_beam_family_integrity(),
        "recipe_book_categorization": verify_recipe_book_categorization(),
        "cache_independence": verify_cache_independence(temp_base),
    }
