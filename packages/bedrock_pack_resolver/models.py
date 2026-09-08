"""Data models, enums, and configuration structures for Bedrock path resolution."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class PackType(str, Enum):
    """Enumeration of Minecraft Bedrock development pack types."""

    BEHAVIOR = "behavior"
    RESOURCE = "resource"
    SKIN = "skin"


PACK_DIRECTORY_MAP: Dict[PackType, str] = {
    PackType.BEHAVIOR: "development_behavior_packs",
    PackType.RESOURCE: "development_resource_packs",
    PackType.SKIN: "development_skin_packs",
}

KNOWN_BEDROCK_PACKAGES: List[str] = [
    "Microsoft.MinecraftWindows_8wekyb3d8bbwe",
    "Microsoft.MinecraftUWP_8wekyb3d8bbwe",
    "Minecraft.Windows_8wekyb3d8bbwe",
    "Microsoft.MinecraftWindowsBeta_8wekyb3d8bbwe",
    "Microsoft.MinecraftBetaUWP_8wekyb3d8bbwe",
    "Microsoft.MinecraftEducationEdition_8wekyb3d8bbwe",
]


class BedrockPathNotFoundError(FileNotFoundError):
    """Exception raised when Minecraft Bedrock cannot be located."""

    def __init__(self, candidates: List[str]):
        """Initialize exception with detailed candidate inspection list.

        Args:
            candidates: List of searched candidate filesystem paths.
        """
        primary = candidates[0] if candidates else "unknown"
        formatted_list = "\n".join(f"  - {path}" for path in candidates)
        message = (
            f"ENOENT: no such file or directory, scandir '{primary}'\n"
            f"Failed to locate active Minecraft Bedrock directory across "
            f"{len(candidates)} candidates:\n{formatted_list}"
        )
        super().__init__(message)
        self.candidates = candidates


@dataclass(frozen=True)
class BedrockResolverOptions:
    """Configuration options for resolving Minecraft Bedrock paths."""

    pack_type: PackType = PackType.BEHAVIOR
    local_app_data: Optional[str] = None
    app_data: Optional[str] = None
    user_profile: Optional[str] = None
    custom_env: Dict[str, str] = field(default_factory=dict)
    auto_create: bool = True
