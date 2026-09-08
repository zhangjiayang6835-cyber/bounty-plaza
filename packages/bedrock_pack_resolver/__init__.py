"""Minecraft Bedrock development packs path resolver package.

Provides robust, zero-admin path discovery across Windows 10/11 retail Store,
Xbox App, legacy UWP, Beta/Preview, and standalone launcher installations.
"""

from packages.bedrock_pack_resolver.models import (
    KNOWN_BEDROCK_PACKAGES,
    PACK_DIRECTORY_MAP,
    BedrockPathNotFoundError,
    BedrockResolverOptions,
    PackType,
)
from packages.bedrock_pack_resolver.resolver import (
    find_minecraft_package_dir,
    get_development_packs_path,
    get_mojang_base_path,
    list_candidate_mojang_paths,
    resolve_dev_packs,
    run_verification_probe,
)

__all__ = [
    "KNOWN_BEDROCK_PACKAGES",
    "PACK_DIRECTORY_MAP",
    "BedrockPathNotFoundError",
    "BedrockResolverOptions",
    "PackType",
    "find_minecraft_package_dir",
    "get_development_packs_path",
    "get_mojang_base_path",
    "list_candidate_mojang_paths",
    "resolve_dev_packs",
    "run_verification_probe",
]
