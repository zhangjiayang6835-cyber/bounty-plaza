"""Data models for Bedrock humanoid entity schemas and geometry definitions."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class CubeDefinition:
    """Represents a 3D box component within a geometry bone."""

    origin: List[float]
    size: List[float]
    uv: List[int]
    inflate: float = 0.0
    mirror: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CubeDefinition":
        """Build CubeDefinition instance from raw dictionary mapping."""
        origin_val = [float(x) for x in data.get("origin", [0.0, 0.0, 0.0])]
        size_val = [float(x) for x in data.get("size", [0.0, 0.0, 0.0])]
        raw_uv = data.get("uv", [0, 0])
        uv_val = [int(x) for x in raw_uv] if isinstance(raw_uv, list) else [0, 0]
        inflate_val = float(data.get("inflate", 0.0))
        mirror_val = bool(data.get("mirror", False))
        return cls(
            origin=origin_val,
            size=size_val,
            uv=uv_val,
            inflate=inflate_val,
            mirror=mirror_val,
        )


@dataclass
class BoneDefinition:
    """Represents a skeletal node bone within Bedrock geometry."""

    name: str
    parent: str = ""
    pivot: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    cubes: List[CubeDefinition] = field(default_factory=list)
    mirror: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BoneDefinition":
        """Build BoneDefinition instance from raw dictionary mapping."""
        name_val = str(data.get("name", ""))
        parent_val = str(data.get("parent", ""))
        pivot_val = [float(x) for x in data.get("pivot", [0.0, 0.0, 0.0])]
        mirror_val = bool(data.get("mirror", False))
        cubes_list = [
            CubeDefinition.from_dict(c) for c in data.get("cubes", [])
        ]
        return cls(
            name=name_val,
            parent=parent_val,
            pivot=pivot_val,
            cubes=cubes_list,
            mirror=mirror_val,
        )


@dataclass
class ClientEntityDescription:
    """Represents client entity description mappings."""

    identifier: str
    materials: Dict[str, str] = field(default_factory=dict)
    textures: Dict[str, str] = field(default_factory=dict)
    geometry: Dict[str, str] = field(default_factory=dict)
    render_controllers: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClientEntityDescription":
        """Build ClientEntityDescription instance from raw dictionary."""
        identifier_val = str(data.get("identifier", ""))
        materials_val = {str(k): str(v) for k, v in data.get("materials", {}).items()}
        textures_val = {str(k): str(v) for k, v in data.get("textures", {}).items()}
        geometry_val = {str(k): str(v) for k, v in data.get("geometry", {}).items()}
        rc_val = [str(rc) for rc in data.get("render_controllers", [])]
        return cls(
            identifier=identifier_val,
            materials=materials_val,
            textures=textures_val,
            geometry=geometry_val,
            render_controllers=rc_val,
        )


@dataclass
class ClientEntityDefinition:
    """Represents a top-level client entity file definition."""

    format_version: str
    description: ClientEntityDescription

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClientEntityDefinition":
        """Build ClientEntityDefinition instance from raw dictionary."""
        version = str(data.get("format_version", "1.10.0"))
        client_entity_raw = data.get("minecraft:client_entity", {})
        desc_raw = client_entity_raw.get("description", {})
        desc = ClientEntityDescription.from_dict(desc_raw)
        return cls(format_version=version, description=desc)


@dataclass
class ValidationIssue:
    """Encapsulates a single validation or architectural compliance issue."""

    severity: str
    code: str
    message: str
    path: str = ""


@dataclass
class ValidationReport:
    """Encapsulates overall validation status and diagnostic details."""

    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    asymmetric_limbs_supported: bool = False
    dual_layer_supported: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    def add_issue(
        self, severity: str, code: str, message: str, path: str = ""
    ) -> None:
        """Append a new issue to the report and adjust validity flag."""
        self.issues.append(
            ValidationIssue(
                severity=severity, code=code, message=message, path=path
            )
        )
        if severity in ("ERROR", "FATAL"):
            self.is_valid = False
