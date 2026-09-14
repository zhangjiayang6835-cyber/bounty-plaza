"""Data models for Bedrock block definitions and validation reports."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ValidationIssue:
    """Represents a single validation issue found during schema checking."""

    path: str
    message: str
    severity: str = "ERROR"

    def to_dict(self) -> Dict[str, str]:
        """Convert validation issue to dictionary format."""
        return {
            "path": self.path,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass
class ValidationReport:
    """Aggregated validation result for a Bedrock block definition."""

    identifier: str
    format_version: str
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)

    def add_error(self, path: str, message: str) -> None:
        """Record an error issue and mark report invalid."""
        self.issues.append(ValidationIssue(path=path, message=message, severity="ERROR"))
        self.is_valid = False

    def add_warning(self, path: str, message: str) -> None:
        """Record a non-fatal warning issue."""
        self.issues.append(ValidationIssue(path=path, message=message, severity="WARNING"))

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary representation."""
        issue_dicts = [issue.to_dict() for issue in self.issues]
        return {
            "identifier": self.identifier,
            "format_version": self.format_version,
            "is_valid": self.is_valid,
            "issues": issue_dicts,
        }


@dataclass
class BlockDescription:
    """Schema model for minecraft:block description section."""

    identifier: str
    menu_category: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None


@dataclass
class ResourcePackBlockConfig:
    """Client-side resource pack configuration for a custom block."""

    identifier: str
    sound: Optional[str] = None
    textures: Optional[Any] = None
    carried_textures: Optional[Any] = None
    isotropic: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert resource pack block config to dictionary."""
        payload: Dict[str, Any] = {}
        if self.sound is not None:
            payload["sound"] = self.sound
        if self.textures is not None:
            payload["textures"] = self.textures
        if self.carried_textures is not None:
            payload["carried_textures"] = self.carried_textures
        if self.isotropic is not None:
            payload["isotropic"] = self.isotropic
        return payload
