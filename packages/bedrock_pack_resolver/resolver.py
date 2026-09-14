"""Core path resolution engine for Minecraft Bedrock development packs."""

import os
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Optional

from packages.bedrock_pack_resolver.models import (
    KNOWN_BEDROCK_PACKAGES,
    PACK_DIRECTORY_MAP,
    BedrockPathNotFoundError,
    BedrockResolverOptions,
    PackType,
)


def find_minecraft_package_dir(packages_dir: str) -> Optional[str]:
    """Scan packages directory for matching Minecraft installations.

    Args:
        packages_dir: Path string to the Windows Packages folder.

    Returns:
        String path to detected package folder, or None if not found.
    """
    pkg_path = Path(packages_dir)
    if not pkg_path.exists():
        return None

    for known_name in KNOWN_BEDROCK_PACKAGES:
        candidate = pkg_path / known_name
        mojang_check = candidate / "LocalState" / "games" / "com.mojang"
        if mojang_check.exists() or candidate.exists():
            return str(candidate)

    try:
        for entry in pkg_path.iterdir():
            if not entry.is_dir():
                continue
            lower_name = entry.name.lower()
            is_mc = "minecraft" in lower_name
            is_valid_prefix = lower_name.startswith("microsoft.") or lower_name.startswith(
                "minecraft."
            )
            if is_mc and is_valid_prefix:
                mojang_check = entry / "LocalState" / "games" / "com.mojang"
                if mojang_check.exists():
                    return str(entry)
    except OSError:
        return None

    return None


def resolve_local_app_data(opts: BedrockResolverOptions, env: Dict[str, str]) -> Path:
    """Resolve the LocalAppData directory path.

    Args:
        opts: Configuration options.
        env: Environment variable dictionary.

    Returns:
        Path object pointing to local application data.
    """
    if opts.local_app_data:
        return Path(opts.local_app_data)
    if env.get("LOCALAPPDATA"):
        return Path(env["LOCALAPPDATA"])
    if opts.user_profile or env.get("USERPROFILE"):
        profile = Path(opts.user_profile or env.get("USERPROFILE", ""))
        return profile / "AppData" / "Local"
    return Path.home() / "AppData" / "Local"


def resolve_roaming_app_data(opts: BedrockResolverOptions, env: Dict[str, str]) -> Path:
    """Resolve the Roaming AppData directory path.

    Args:
        opts: Configuration options.
        env: Environment variable dictionary.

    Returns:
        Path object pointing to roaming application data.
    """
    if opts.app_data:
        return Path(opts.app_data)
    if env.get("APPDATA"):
        return Path(env["APPDATA"])
    if opts.user_profile or env.get("USERPROFILE"):
        profile = Path(opts.user_profile or env.get("USERPROFILE", ""))
        return profile / "AppData" / "Roaming"
    return Path.home() / "AppData" / "Roaming"


def collect_package_candidates(packages_dir: Path) -> List[str]:
    """Collect candidate com.mojang paths from packages directory.

    Args:
        packages_dir: Path to Packages directory.

    Returns:
        List of candidate filesystem paths.
    """
    candidates: List[str] = []
    discovered = find_minecraft_package_dir(str(packages_dir))
    if discovered:
        disc_mojang = Path(discovered) / "LocalState" / "games" / "com.mojang"
        candidates.append(str(disc_mojang))

    for pkg_name in KNOWN_BEDROCK_PACKAGES:
        pkg_mojang = packages_dir / pkg_name / "LocalState" / "games" / "com.mojang"
        str_path = str(pkg_mojang)
        if str_path not in candidates:
            candidates.append(str_path)
    return candidates


def list_candidate_mojang_paths(
    options: Optional[BedrockResolverOptions] = None,
) -> List[str]:
    """Generate an ordered list of candidate paths to com.mojang.

    Args:
        options: Configuration options or mock environment.

    Returns:
        Ordered list of candidate filesystem paths to inspect.
    """
    opts = options or BedrockResolverOptions()
    env = {**os.environ, **opts.custom_env}
    candidates: List[str] = []

    direct_path = env.get("MINECRAFT_BEDROCK_PATH")
    if direct_path:
        path_obj = Path(direct_path)
        if direct_path.endswith("com.mojang"):
            candidates.append(str(path_obj))
        else:
            candidates.append(str(path_obj / "games" / "com.mojang"))
            candidates.append(str(path_obj / "LocalState" / "games" / "com.mojang"))
            candidates.append(str(path_obj))

    local_app_data = resolve_local_app_data(opts, env)
    roaming_app_data = resolve_roaming_app_data(opts, env)
    packages_dir = local_app_data / "Packages"

    candidates.extend(collect_package_candidates(packages_dir))

    candidates.append(str(local_app_data / "Minecraft" / "LocalState" / "games" / "com.mojang"))
    candidates.append(
        str(local_app_data / "Minecraft Bedrock" / "LocalState" / "games" / "com.mojang")
    )
    candidates.append(str(local_app_data / "Minecraft" / "games" / "com.mojang"))
    candidates.append(str(roaming_app_data / "Minecraft Bedrock" / "games" / "com.mojang"))

    return candidates


def get_mojang_base_path(options: Optional[BedrockResolverOptions] = None) -> str:
    """Resolve the com.mojang directory path across supported installations.

    Args:
        options: Configuration options or mock environment.

    Returns:
        The resolved absolute path to com.mojang.

    Raises:
        BedrockPathNotFoundError: If no candidate path exists on the filesystem.
    """
    candidates = list_candidate_mojang_paths(options)

    for candidate in candidates:
        if Path(candidate).exists():
            return candidate

    raise BedrockPathNotFoundError(candidates)


def get_development_packs_path(
    options: Optional[BedrockResolverOptions] = None,
) -> str:
    """Resolve active Minecraft Bedrock development packs directory.

    Args:
        options: Configuration options or mock environment.

    Returns:
        Absolute path to the development pack folder.

    Raises:
        BedrockPathNotFoundError: If parent directory cannot be resolved.
        FileNotFoundError: If auto_create is False and directory is missing.
    """
    opts = options or BedrockResolverOptions()
    env = {**os.environ, **opts.custom_env}

    override_path = env.get("MINECRAFT_DEV_PACKS_PATH")
    if override_path and Path(override_path).exists():
        return override_path

    pack_folder = PACK_DIRECTORY_MAP.get(opts.pack_type, PACK_DIRECTORY_MAP[PackType.BEHAVIOR])
    mojang_base = Path(get_mojang_base_path(opts))
    target_path = mojang_base / pack_folder

    if not target_path.exists():
        if opts.auto_create:
            target_path.mkdir(parents=True, exist_ok=True)
        else:
            raise FileNotFoundError(
                f"ENOENT: no such file or directory, scandir '{target_path}'"
            )

    return str(target_path)


def resolve_dev_packs(options: Optional[BedrockResolverOptions] = None) -> str:
    """Alias for get_development_packs_path matching CLI convention.

    Args:
        options: Configuration options or mock environment.

    Returns:
        Absolute path to resolved development packs directory.
    """
    return get_development_packs_path(options)


def run_verification_probe() -> Dict[str, Any]:
    """Execute end-to-end verification probe against temporary mock environments.

    Returns:
        Dictionary containing verified capabilities and metrics.
    """
    with tempfile.TemporaryDirectory() as probe_dir:
        sandbox = Path(probe_dir)
        local_dir = sandbox / "Local"
        active_store_pkg = (
            local_dir
            / "Packages"
            / "Microsoft.MinecraftWindows_8wekyb3d8bbwe"
            / "LocalState"
            / "games"
            / "com.mojang"
        )
        active_store_pkg.mkdir(parents=True)

        opts_behavior = BedrockResolverOptions(
            local_app_data=str(local_dir),
            pack_type=PackType.BEHAVIOR,
            auto_create=True,
        )
        resolved_behavior = get_development_packs_path(opts_behavior)

        opts_resource = BedrockResolverOptions(
            local_app_data=str(local_dir),
            pack_type=PackType.RESOURCE,
            auto_create=True,
        )
        resolved_resource = get_development_packs_path(opts_resource)

        candidates = list_candidate_mojang_paths(opts_behavior)

        missing_caught = False
        empty_sandbox = sandbox / "Empty"
        empty_sandbox.mkdir(parents=True)
        try:
            get_development_packs_path(BedrockResolverOptions(local_app_data=str(empty_sandbox)))
        except BedrockPathNotFoundError:
            missing_caught = True

    return {
        "behavior_resolved": resolved_behavior.endswith("development_behavior_packs"),
        "resource_resolved": resolved_resource.endswith("development_resource_packs"),
        "candidate_count": len(candidates),
        "missing_caught": missing_caught,
    }
