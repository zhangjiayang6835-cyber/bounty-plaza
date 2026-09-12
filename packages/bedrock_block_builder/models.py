"""Domain models and data definitions for Bedrock block family building."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class BlockShape(str, Enum):
    """Enumeration of recognized Minecraft Bedrock block structural shapes."""

    BASE = "base"
    SLAB = "slab"
    DOUBLE_SLAB = "double_slab"
    STAIR = "stair"
    WALL = "wall"
    FENCE = "fence"
    FENCE_GATE = "fence_gate"
    PILLAR = "pillar"
    POST = "post"
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"
    STRIPPED = "stripped"
    CORNER = "corner"
    CARVED = "carved"


class RecipeCategory(str, Enum):
    """Enumeration of Bedrock recipe book UI categories."""

    CONSTRUCTION = "construction"
    EQUIPMENT = "equipment"
    ITEMS = "items"
    NATURE = "nature"
    NONE = "none"


class FamilyValidationError(Exception):
    """Raised when block families or required registry entries fail validation."""

    def __init__(self, message: str, missing_definitions: Optional[list[str]] = None) -> None:
        """Initializes the validation error with details and missing identifiers."""
        super().__init__(message)
        self.message = message
        self.missing_definitions = missing_definitions or []


@dataclass
class BlockDefinition:
    """Represents a single parsed or staged Minecraft Bedrock block definition."""

    identifier: str
    family: str
    shape: BlockShape = BlockShape.BASE
    category: RecipeCategory = RecipeCategory.CONSTRUCTION
    group: str = ""
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serializes the block definition to a dictionary representation."""
        return {
            "identifier": self.identifier,
            "family": self.family,
            "shape": self.shape.value,
            "category": self.category.value,
            "group": self.group,
            "properties": self.properties,
        }


@dataclass
class BlockFamily:
    """Represents a grouped family of related blocks sharing a root identity."""

    name: str
    base_block: str
    members: dict[str, str] = field(default_factory=dict)
    recipe_category: RecipeCategory = RecipeCategory.CONSTRUCTION

    def add_member(self, shape: str, identifier: str) -> None:
        """Registers a member shape mapping within this family."""
        self.members[shape] = identifier

    def get_member(self, shape: str) -> Optional[str]:
        """Retrieves the block identifier assigned to a specific shape."""
        return self.members.get(shape)

    def to_dict(self) -> dict[str, Any]:
        """Serializes the block family to a dictionary representation."""
        return {
            "name": self.name,
            "base_block": self.base_block,
            "members": self.members,
            "recipe_category": self.recipe_category.value,
        }


@dataclass
class CatalogStatistics:
    """Summary metrics of compiled block families and registry categorizations."""

    total_families: int = 0
    total_blocks: int = 0
    shape_counts: dict[str, int] = field(default_factory=dict)
    category_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serializes statistics to a dictionary representation."""
        return {
            "total_families": self.total_families,
            "total_blocks": self.total_blocks,
            "shape_counts": self.shape_counts,
            "category_counts": self.category_counts,
        }


@dataclass
class BlockFamilyCatalog:
    """Complete catalog containing all compiled block families and registry mappings."""

    format_version: str = "1.20.80"
    families: dict[str, BlockFamily] = field(default_factory=dict)
    block_to_family: dict[str, str] = field(default_factory=dict)
    recipe_categories: dict[str, list[str]] = field(default_factory=dict)
    checksum: str = ""
    statistics: CatalogStatistics = field(default_factory=CatalogStatistics)

    def to_dict(self) -> dict[str, Any]:
        """Serializes the complete catalog to a dictionary representation."""
        return {
            "format_version": self.format_version,
            "checksum": self.checksum,
            "statistics": self.statistics.to_dict(),
            "families": {name: fam.to_dict() for name, fam in self.families.items()},
            "block_to_family": self.block_to_family,
            "recipe_categories": self.recipe_categories,
        }


@dataclass
class BuildOptions:
    """Configuration options governing Bedrock pack compilation and cataloging."""

    source_dir: str = "packs/behavior_pack"
    staging_base: str = "_temp"
    staging_dir: str = "_temp/behavior_pack"
    dest_dir: str = "dist/behavior_pack"
    catalog_path: str = ""
    clean: bool = True
    require_existing: bool = False


@dataclass
class BuildResult:
    """Outcome report for a Bedrock pack build and catalog generation cycle."""

    success: bool
    catalog: Optional[BlockFamilyCatalog] = None
    staged_files: int = 0
    errors: list[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serializes the build result to a dictionary representation."""
        return {
            "success": self.success,
            "staged_files": self.staged_files,
            "errors": self.errors,
            "message": self.message,
            "catalog": self.catalog.to_dict() if self.catalog else None,
        }
