"""Block family metadata catalog generator and registry compiler."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Optional

from packages.bedrock_block_builder.models import (
    BlockDefinition,
    BlockFamily,
    BlockFamilyCatalog,
    BlockShape,
    BuildOptions,
    CatalogStatistics,
    FamilyValidationError,
    RecipeCategory,
)

SHAPE_SUFFIX_TABLE = (
    ("_double_slab", BlockShape.DOUBLE_SLAB),
    ("_slab", BlockShape.SLAB),
    ("_stair", BlockShape.STAIR),
    ("_fence_gate", BlockShape.FENCE_GATE),
    ("_fence", BlockShape.FENCE),
    ("_wall", BlockShape.WALL),
    ("_vertical", BlockShape.VERTICAL),
    ("_horizontal", BlockShape.HORIZONTAL),
    ("_stripped", BlockShape.STRIPPED),
    ("_corner", BlockShape.CORNER),
    ("_pillar", BlockShape.PILLAR),
    ("_post", BlockShape.POST),
    ("_carved", BlockShape.CARVED),
)


def determine_shape(identifier: str, block_data: Optional[dict[str, Any]] = None) -> BlockShape:
    """Determines structural block shape from identifier naming conventions and metadata."""
    clean_id = identifier.lower()

    for suffix, shape in SHAPE_SUFFIX_TABLE:
        if clean_id.endswith(suffix):
            return shape

    keyword_shapes = (
        ("slab", BlockShape.SLAB),
        ("stair", BlockShape.STAIR),
        ("wall", BlockShape.WALL),
    )
    for kw, shape in keyword_shapes:
        if kw in clean_id:
            return shape

    if block_data:
        components = block_data.get("minecraft:block", {}).get("components", {})
        geo = str(components.get("minecraft:geometry", "")).lower()
        if "slab" in geo:
            return BlockShape.SLAB
        if "stair" in geo:
            return BlockShape.STAIR

    return BlockShape.BASE


def determine_family(identifier: str, block_data: Optional[dict[str, Any]] = None) -> str:
    """Extracts canonical family name by stripping structural variant suffixes."""
    if block_data:
        custom_family = (
            block_data.get("minecraft:block", {})
            .get("description", {})
            .get("family")
        )
        if custom_family:
            return str(custom_family)

    parts = identifier.split(":", 1)
    prefix = f"{parts[0]}:" if len(parts) > 1 else ""
    local_name = parts[1] if len(parts) > 1 else parts[0]

    for suffix, _ in SHAPE_SUFFIX_TABLE:
        if local_name.endswith(suffix):
            local_name = local_name[: -len(suffix)]
            break

    return f"{prefix}{local_name}"


def determine_category(
    identifier: str, block_data: Optional[dict[str, Any]] = None
) -> RecipeCategory:
    """Infers recipe book UI menu category from block declaration."""
    if block_data:
        menu_cat = (
            block_data.get("minecraft:block", {})
            .get("description", {})
            .get("menu_category", {})
            .get("category")
        )
        if menu_cat:
            try:
                return RecipeCategory(str(menu_cat).lower())
            except ValueError:
                pass

    clean_id = identifier.lower()
    if any(k in clean_id for k in ["beam", "plank", "stone", "brick", "slab", "stair", "wall"]):
        return RecipeCategory.CONSTRUCTION
    if any(k in clean_id for k in ["sword", "pickaxe", "axe", "armor", "helmet"]):
        return RecipeCategory.EQUIPMENT
    if any(k in clean_id for k in ["seed", "flower", "log", "leaves", "sapling"]):
        return RecipeCategory.NATURE

    return RecipeCategory.CONSTRUCTION


class BlockFamilyBuilder:
    """Constructs, categorizes, and serializes Bedrock block family catalogs."""

    def __init__(
        self,
        options: Optional[BuildOptions] = None,
        fail_on_missing: bool = True,
    ) -> None:
        """Initializes builder options, paths, and registry storage."""
        opts = options or BuildOptions()
        self.source_dir = Path(opts.source_dir).resolve()
        self.staging_base = Path(opts.staging_base).resolve()
        self.staging_dir = Path(opts.staging_dir).resolve()
        if opts.catalog_path:
            self.catalog_path = Path(opts.catalog_path).resolve()
        else:
            self.catalog_path = (self.staging_base / "block_families.json").resolve()

        self.require_existing = opts.require_existing
        self.fail_on_missing = fail_on_missing
        self.definitions: dict[str, BlockDefinition] = {}

    def add_definition(self, definition: BlockDefinition) -> None:
        """Explicitly registers a block definition in builder memory."""
        self.definitions[definition.identifier] = definition

    def collect_block_files(self, directory: Path) -> list[Path]:
        """Recursively discovers all JSON block files within target path."""
        if not directory.exists():
            return []
        found: list[Path] = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".json"):
                    found.append(Path(root) / file)
        return sorted(found)

    def parse_block_file(self, file_path: Path) -> Optional[BlockDefinition]:
        """Parses a Minecraft Bedrock block JSON file into a BlockDefinition."""
        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, OSError):
            return None

        block_node = data.get("minecraft:block")
        if not isinstance(block_node, dict):
            return None

        desc = block_node.get("description", {})
        identifier = desc.get("identifier")
        if not identifier or not isinstance(identifier, str):
            return None

        shape = determine_shape(identifier, data)
        family = determine_family(identifier, data)
        category = determine_category(identifier, data)
        group = desc.get("menu_category", {}).get("group", "")

        return BlockDefinition(
            identifier=identifier,
            family=family,
            shape=shape,
            category=category,
            group=group,
            properties=block_node.get("properties", {}),
        )

    def scan_directory(self, target_dir: Optional[Path] = None) -> int:
        """Scans specified or default directory and loads block definitions."""
        directory = target_dir or self.staging_dir
        if not directory.exists():
            directory = self.source_dir

        files = self.collect_block_files(directory)
        count = 0
        for file in files:
            defn = self.parse_block_file(file)
            if defn:
                self.definitions[defn.identifier] = defn
                count += 1
        return count

    def _compile_groupings(
        self,
    ) -> tuple[dict[str, BlockFamily], dict[str, str], dict[str, list[str]], CatalogStatistics]:
        """Compiles block groupings, mappings, and calculates catalog statistics."""
        families: dict[str, BlockFamily] = {}
        block_to_family: dict[str, str] = {}
        recipe_categories: dict[str, list[str]] = {
            cat.value: [] for cat in RecipeCategory if cat != RecipeCategory.NONE
        }
        shape_counts: dict[str, int] = {}
        category_counts: dict[str, int] = {}

        for defn in sorted(self.definitions.values(), key=lambda d: d.identifier):
            fam_name = defn.family
            if fam_name not in families:
                base_block = defn.identifier if defn.shape == BlockShape.BASE else ""
                families[fam_name] = BlockFamily(
                    name=fam_name,
                    base_block=base_block,
                    members={},
                    recipe_category=defn.category,
                )

            family = families[fam_name]
            family.add_member(defn.shape.value, defn.identifier)
            if not family.base_block and defn.shape == BlockShape.BASE:
                family.base_block = defn.identifier

            block_to_family[defn.identifier] = fam_name
            cat_val = defn.category.value
            if cat_val in recipe_categories:
                recipe_categories[cat_val].append(defn.identifier)

            shape_counts[defn.shape.value] = shape_counts.get(defn.shape.value, 0) + 1
            category_counts[cat_val] = category_counts.get(cat_val, 0) + 1

        for fam in families.values():
            if not fam.base_block and fam.members:
                fam.base_block = next(iter(fam.members.values()))

        stats = CatalogStatistics(
            total_families=len(families),
            total_blocks=len(self.definitions),
            shape_counts=shape_counts,
            category_counts=category_counts,
        )
        return families, block_to_family, recipe_categories, stats

    def build_catalog(self, scan_dir: Optional[Path] = None) -> BlockFamilyCatalog:
        """Builds and returns validated BlockFamilyCatalog."""
        if self.require_existing and not self.catalog_path.exists():
            raise FamilyValidationError(
                f"Missing block family catalog: '{self.catalog_path}' not found."
            )

        if scan_dir or not self.definitions:
            self.scan_directory(scan_dir)

        families, block_to_family, categories, stats = self._compile_groupings()

        canonical_data = {
            "format_version": "1.20.80",
            "families": {name: fam.to_dict() for name, fam in sorted(families.items())},
            "block_to_family": dict(sorted(block_to_family.items())),
            "recipe_categories": {k: sorted(v) for k, v in sorted(categories.items())},
        }
        encoded = json.dumps(canonical_data, sort_keys=True).encode("utf-8")
        checksum = hashlib.sha256(encoded).hexdigest()

        catalog = BlockFamilyCatalog(
            format_version="1.20.80",
            families=families,
            block_to_family=block_to_family,
            recipe_categories=categories,
            checksum=checksum,
            statistics=stats,
        )

        validation_errors = self.validate_catalog(catalog)
        if validation_errors and self.fail_on_missing:
            formatted_errors = "\n".join(validation_errors)
            raise FamilyValidationError(
                f"Block family validation failed:\n{formatted_errors}",
                missing_definitions=validation_errors,
            )

        return catalog

    def validate_catalog(self, catalog: BlockFamilyCatalog) -> list[str]:
        """Validates catalog integrity ensuring all member blocks resolve correctly."""
        errors: list[str] = []
        for fam_name, family in catalog.families.items():
            if not family.base_block:
                errors.append(f"Undefined base block for family: '{fam_name}'")
            for shape, block_id in family.members.items():
                if block_id not in catalog.block_to_family:
                    errors.append(
                        f"Undefined block family reference: '{block_id}' in shape '{shape}'"
                    )
        return errors

    def export_catalog(
        self, catalog: BlockFamilyCatalog, target_path: Optional[Path] = None
    ) -> Path:
        """Writes catalog JSON deterministically to target or configured path."""
        out_path = target_path or self.catalog_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump(catalog.to_dict(), handle, indent=2, sort_keys=True)
            handle.write("\n")
        return out_path


def generate_block_families(
    options: Optional[BuildOptions] = None,
    fail_on_missing: bool = True,
) -> BlockFamilyCatalog:
    """Functional convenience entrypoint to construct and export a catalog."""
    builder = BlockFamilyBuilder(
        options=options,
        fail_on_missing=fail_on_missing,
    )
    catalog = builder.build_catalog()
    builder.export_catalog(catalog)
    return catalog
