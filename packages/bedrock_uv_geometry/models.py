"""Data models for Minecraft Bedrock entity geometries and UV mappings."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union


class ArmModelType(str, Enum):
    """Player and NPC arm geometry variants."""

    CLASSIC = "classic"
    SLIM = "slim"


class ValidationSeverity(str, Enum):
    """Severity classification for geometry and UV inspection results."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Individual diagnostics entry generated during validation."""

    code: str
    message: str
    bone_name: Optional[str] = None
    severity: ValidationSeverity = ValidationSeverity.ERROR


@dataclass
class ValidationReport:
    """Consolidated report detailing geometry validity and detected defects."""

    is_valid: bool = True
    issues: list[ValidationIssue] = field(default_factory=list)

    def add_issue(
        self,
        code: str,
        message: str,
        bone_name: Optional[str] = None,
        severity: ValidationSeverity = ValidationSeverity.ERROR,
    ) -> None:
        """Append an issue and update overall validity state."""
        self.issues.append(
            ValidationIssue(
                code=code,
                message=message,
                bone_name=bone_name,
                severity=severity,
            )
        )
        if severity == ValidationSeverity.ERROR:
            self.is_valid = False

    def has_code(self, code: str) -> bool:
        """Check if any recorded issue matches the specified diagnostic code."""
        return any(issue.code == code for issue in self.issues)

    def errors(self) -> list[ValidationIssue]:
        """Return all issues categorized as errors."""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.ERROR]

    def warnings(self) -> list[ValidationIssue]:
        """Return all issues categorized as warnings."""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.WARNING]


@dataclass
class Cube:
    """Cubic element forming a part of a bone's mesh."""

    origin: tuple[float, float, float]
    size: tuple[float, float, float]
    uv: Union[tuple[float, float], dict[str, Any]]
    inflate: float = 0.0
    mirror: Optional[bool] = None

    @property
    def is_box_uv(self) -> bool:
        """Determine whether cube utilizes standard 2D box UV offset coordinates."""
        return isinstance(self.uv, (list, tuple))

    def to_dict(self) -> dict[str, Any]:
        """Serialize cube definition into compliant Bedrock JSON dictionary."""
        cube_dict: dict[str, Any] = {
            "origin": list(self.origin),
            "size": list(self.size),
        }
        if self.is_box_uv:
            cube_dict["uv"] = list(self.uv)  # type: ignore[arg-type]
        else:
            cube_dict["uv"] = self.uv

        if self.inflate != 0.0:
            cube_dict["inflate"] = self.inflate
        if self.mirror is not None:
            cube_dict["mirror"] = self.mirror

        return cube_dict

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Cube":
        """Construct cube instance from raw dictionary data."""
        raw_origin = data.get("origin", [0.0, 0.0, 0.0])
        raw_size = data.get("size", [0.0, 0.0, 0.0])
        raw_uv = data.get("uv", [0.0, 0.0])

        origin = (float(raw_origin[0]), float(raw_origin[1]), float(raw_origin[2]))
        size = (float(raw_size[0]), float(raw_size[1]), float(raw_size[2]))

        uv_value: Union[tuple[float, float], dict[str, Any]]
        if isinstance(raw_uv, (list, tuple)) and len(raw_uv) >= 2:
            uv_value = (float(raw_uv[0]), float(raw_uv[1]))
        elif isinstance(raw_uv, dict):
            uv_value = raw_uv
        else:
            uv_value = (0.0, 0.0)

        inflate = float(data.get("inflate", 0.0))
        mirror = data.get("mirror", None)

        return cls(origin=origin, size=size, uv=uv_value, inflate=inflate, mirror=mirror)


@dataclass
class Bone:
    """Hierarchical bone definition within a Bedrock skeletal rig."""

    name: str
    parent: Optional[str] = None
    pivot: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    cubes: list[Cube] = field(default_factory=list)
    neverrender: bool = False
    mirror: Optional[bool] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize bone structure to Bedrock specification."""
        bone_dict: dict[str, Any] = {"name": self.name}
        if self.parent:
            bone_dict["parent"] = self.parent

        bone_dict["pivot"] = list(self.pivot)
        if any(rot != 0.0 for rot in self.rotation):
            bone_dict["rotation"] = list(self.rotation)

        if self.neverrender:
            bone_dict["neverrender"] = True
        if self.mirror is not None:
            bone_dict["mirror"] = self.mirror

        if self.cubes:
            bone_dict["cubes"] = [cube.to_dict() for cube in self.cubes]

        return bone_dict

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Bone":
        """Instantiate bone model from dictionary structure."""
        name = data.get("name", "")
        parent = data.get("parent", None)

        raw_pivot = data.get("pivot", [0.0, 0.0, 0.0])
        pivot = (float(raw_pivot[0]), float(raw_pivot[1]), float(raw_pivot[2]))

        raw_rot = data.get("rotation", [0.0, 0.0, 0.0])
        rotation = (float(raw_rot[0]), float(raw_rot[1]), float(raw_rot[2]))

        cubes_raw = data.get("cubes", [])
        cubes = [Cube.from_dict(c) for c in cubes_raw]

        neverrender = bool(data.get("neverrender", False))
        mirror = data.get("mirror", None)

        return cls(
            name=name,
            parent=parent,
            pivot=pivot,
            rotation=rotation,
            cubes=cubes,
            neverrender=neverrender,
            mirror=mirror,
        )


@dataclass
class GeometryDescription:
    """Header metadata defining texture bounds and culling dimensions."""

    identifier: str
    texture_width: int = 64
    texture_height: int = 64
    visible_bounds_width: float = 1.5
    visible_bounds_height: float = 2.0
    visible_bounds_offset: tuple[float, float, float] = (0.0, 1.0, 0.0)

    def to_dict(self) -> dict[str, Any]:
        """Serialize metadata to dictionary."""
        return {
            "identifier": self.identifier,
            "texture_width": self.texture_width,
            "texture_height": self.texture_height,
            "visible_bounds_width": self.visible_bounds_width,
            "visible_bounds_height": self.visible_bounds_height,
            "visible_bounds_offset": list(self.visible_bounds_offset),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GeometryDescription":
        """Create description instance from dictionary."""
        identifier = data.get("identifier", "")
        texture_width = int(data.get("texture_width", 64))
        texture_height = int(data.get("texture_height", 64))
        bounds_w = float(data.get("visible_bounds_width", 1.5))
        bounds_h = float(data.get("visible_bounds_height", 2.0))
        raw_offset = data.get("visible_bounds_offset", [0.0, 1.0, 0.0])
        bounds_offset = (float(raw_offset[0]), float(raw_offset[1]), float(raw_offset[2]))

        return cls(
            identifier=identifier,
            texture_width=texture_width,
            texture_height=texture_height,
            visible_bounds_width=bounds_w,
            visible_bounds_height=bounds_h,
            visible_bounds_offset=bounds_offset,
        )


@dataclass
class BedrockGeometry:
    """Root model representing complete Bedrock geometry document."""

    description: GeometryDescription
    bones: list[Bone] = field(default_factory=list)
    format_version: str = "1.12.0"

    def get_bone(self, name: str) -> Optional[Bone]:
        """Retrieve bone matching specified name identifier."""
        for bone in self.bones:
            if bone.name == name:
                return bone
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert geometry to canonical Bedrock JSON schema format."""
        return {
            "format_version": self.format_version,
            "minecraft:geometry": [
                {
                    "description": self.description.to_dict(),
                    "bones": [bone.to_dict() for bone in self.bones],
                }
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BedrockGeometry":
        """Parse raw Bedrock geometry JSON object into strongly typed model."""
        format_version = data.get("format_version", "1.12.0")
        geo_list = data.get("minecraft:geometry", [])
        if not geo_list:
            raise ValueError("Missing 'minecraft:geometry' array in payload")

        primary = geo_list[0]
        desc_raw = primary.get("description", {})
        description = GeometryDescription.from_dict(desc_raw)

        bones_raw = primary.get("bones", [])
        bones = [Bone.from_dict(b) for b in bones_raw]

        return cls(description=description, bones=bones, format_version=format_version)
