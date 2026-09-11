"""Data models and representations for Bedrock block definitions and schema validation."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class RenderMethod(str, Enum):
    """Allowed Bedrock block material render methods."""

    OPAQUE = "opaque"
    ALPHA_TEST = "alpha_test"
    ALPHA_TEST_SINGLE_SIDED = "alpha_test_single_sided"
    BLEND = "blend"
    DOUBLE_SIDED = "double_sided"


class FaceDirection(str, Enum):
    """Valid directional face specifiers for block material instances."""

    UP = "up"
    DOWN = "down"
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    ALL = "*"


@dataclass(frozen=True)
class MaterialInstance:
    """Represents a single material instance face configuration."""

    texture: str
    render_method: RenderMethod = RenderMethod.OPAQUE
    face_dimming: bool = True
    ambient_occlusion: float = 1.0
    isotropic: Optional[bool] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert material instance to a dictionary adhering to Bedrock schema."""
        data: dict[str, Any] = {
            "texture": self.texture,
            "render_method": self.render_method.value,
            "face_dimming": self.face_dimming,
            "ambient_occlusion": self.ambient_occlusion,
        }
        if self.isotropic is not None:
            data["isotropic"] = self.isotropic
        return data


@dataclass
class BlockDescription:
    """Represents metadata and identification for a custom block."""

    identifier: str
    menu_category: dict[str, Any] = field(default_factory=dict)
    states: dict[str, list[Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert block description to JSON-compatible dictionary."""
        data: dict[str, Any] = {"identifier": self.identifier}
        if self.menu_category:
            data["menu_category"] = self.menu_category
        if self.states:
            data["states"] = self.states
        return data


@dataclass
class BlockComponents:
    """Represents core components assigned to a Bedrock block."""

    material_instances: dict[str, MaterialInstance] = field(default_factory=dict)
    geometry: dict[str, Any] = field(default_factory=dict)
    collision_box: dict[str, Any] = field(default_factory=dict)
    selection_box: dict[str, Any] = field(default_factory=dict)
    destructible_by_mining: dict[str, Any] = field(default_factory=dict)
    destructible_by_explosion: dict[str, Any] = field(default_factory=dict)
    friction: float = 0.6
    map_color: str = "#474F52"

    def to_dict(self) -> dict[str, Any]:
        """Convert block components to Bedrock block components dictionary."""
        res: dict[str, Any] = {
            "minecraft:destructible_by_mining": self.destructible_by_mining,
            "minecraft:destructible_by_explosion": self.destructible_by_explosion,
            "minecraft:friction": self.friction,
            "minecraft:map_color": self.map_color,
            "minecraft:selection_box": self.selection_box,
            "minecraft:collision_box": self.collision_box,
            "minecraft:geometry": self.geometry,
            "minecraft:material_instances": {
                k: v.to_dict() for k, v in self.material_instances.items()
            },
        }
        return res


@dataclass
class BedrockBlockDefinition:
    """Represents a complete Bedrock block definition document."""

    format_version: str
    description: BlockDescription
    components: BlockComponents

    def to_dict(self) -> dict[str, Any]:
        """Convert full block definition to JSON-compatible structure."""
        return {
            "format_version": self.format_version,
            "minecraft:block": {
                "description": self.description.to_dict(),
                "components": self.components.to_dict(),
            },
        }


@dataclass(frozen=True)
class ValidationIssue:
    """Represents an error or warning encountered during schema validation."""

    code: str
    message: str
    severity: str = "ERROR"


@dataclass
class ValidationReport:
    """Aggregated report of schema validation containing status and issues."""

    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    def has_code(self, code: str) -> bool:
        """Check whether an issue with the given code exists."""
        return any(issue.code == code for issue in self.issues)

    def error_messages(self) -> list[str]:
        """Extract all issue messages as a list of strings."""
        return [issue.message for issue in self.issues]
