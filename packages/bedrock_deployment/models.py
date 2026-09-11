"""Data models and enums for Bedrock deployment path resolution and pack delivery."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class PlatformType(str, Enum):
    """Supported operating system platform classifications."""

    WINDOWS = "win32"
    DARWIN = "darwin"
    LINUX = "linux"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class PackType(str, Enum):
    """Bedrock pack architecture category."""

    BEHAVIOR = "behavior"
    RESOURCE = "resource"


@dataclass(frozen=True)
class PathCandidate:
    """Represents an evaluated filesystem candidate location."""

    path: Path
    platform: PlatformType
    is_uwp: bool
    priority: int
    exists: bool

    def as_dict(self) -> dict[str, object]:
        """Convert candidate to serialized dictionary representation."""
        return {
            "path": str(self.path),
            "platform": self.platform.value,
            "is_uwp": self.is_uwp,
            "priority": self.priority,
            "exists": self.exists,
        }


@dataclass
class DeploymentConfig:
    """Configuration governing pack deployment execution."""

    source_dir: Path
    target_dir: Optional[Path] = None
    pack_type: PackType = PackType.BEHAVIOR
    auto_create: bool = True
    fallback_to_local: bool = True
    dry_run: bool = False
    clean_slate: bool = True


@dataclass
class DeploymentResult:
    """Execution telemetry and outcome of pack deployment."""

    success: bool
    destination: Path
    files_copied: int
    files_removed: int
    fallback_used: bool
    warnings: list[str] = field(default_factory=list)
    error_message: Optional[str] = None

    def as_dict(self) -> dict[str, object]:
        """Serialize deployment outcome to dictionary."""
        return {
            "success": self.success,
            "destination": str(self.destination),
            "files_copied": self.files_copied,
            "files_removed": self.files_removed,
            "fallback_used": self.fallback_used,
            "warnings": list(self.warnings),
            "error_message": self.error_message,
        }
