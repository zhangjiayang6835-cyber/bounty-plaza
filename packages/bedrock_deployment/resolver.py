"""Bedrock development path resolver supporting modern Windows 11 roaming and UWP stores."""

from dataclasses import dataclass
import os
from pathlib import Path
import sys
from typing import Optional

from .models import PackType, PathCandidate, PlatformType


KNOWN_UWP_PACKAGES = (
    "Microsoft.MinecraftUWP_8wekyb3d8bbwe",
    "Microsoft.MinecraftWindows_8wekyb3d8bbwe",
    "Minecraft.Windows_8wekyb3d8bbwe",
)


@dataclass
class ResolverOptions:
    """Configuration options for path resolution."""

    pack_type: PackType = PackType.BEHAVIOR
    custom_destination: Optional[Path] = None
    platform_type: Optional[PlatformType] = None
    env_vars: Optional[dict[str, str]] = None
    home_dir: Optional[Path] = None
    auto_create: bool = True
    local_dist_root: Optional[Path] = None


class BedrockPathResolver:
    """Discovers and resolves development pack destination paths across operating systems."""

    @staticmethod
    def detect_platform(platform_str: Optional[str] = None) -> PlatformType:
        """Identify runtime platform classification from identifier or sys.platform."""
        raw = (platform_str or sys.platform).lower()
        if "win" in raw:
            return PlatformType.WINDOWS
        if "darwin" in raw:
            return PlatformType.DARWIN
        if "linux" in raw:
            return PlatformType.LINUX
        return PlatformType.UNKNOWN

    @staticmethod
    def get_subfolder_name(pack_type: PackType) -> str:
        """Return standardized Bedrock development subfolder directory name."""
        if pack_type == PackType.RESOURCE:
            return "development_resource_packs"
        return "development_behavior_packs"

    @classmethod
    def _build_uwp_candidates(cls, packages_root: Path, subfolder: str) -> list[PathCandidate]:
        """Generate candidates from known UWP package identifiers."""
        result: list[PathCandidate] = []
        for idx, pkg_name in enumerate(KNOWN_UWP_PACKAGES):
            target = packages_root / pkg_name / "LocalState" / "games" / "com.mojang" / subfolder
            result.append(
                PathCandidate(
                    path=target,
                    platform=PlatformType.WINDOWS,
                    is_uwp=True,
                    priority=40 + (idx * 10),
                    exists=target.exists(),
                )
            )
        return result

    @classmethod
    def generate_windows_candidates(
        cls, env_vars: dict[str, str], home_dir: Path, subfolder: str
    ) -> list[PathCandidate]:
        """Generate ranked list of possible Windows filesystem deployment locations."""
        candidates: list[PathCandidate] = []
        appdata_val = env_vars.get("APPDATA")
        appdata = Path(appdata_val) if appdata_val else home_dir / "AppData" / "Roaming"

        local_val = env_vars.get("LOCALAPPDATA")
        localappdata = Path(local_val) if local_val else home_dir / "AppData" / "Local"

        roaming_bedrock = appdata / ".minecraft" / "bedrock" / subfolder
        candidates.append(
            PathCandidate(
                path=roaming_bedrock,
                platform=PlatformType.WINDOWS,
                is_uwp=False,
                priority=10,
                exists=roaming_bedrock.exists(),
            )
        )

        roaming_pe = appdata / "Minecraftpe" / "games" / "com.mojang" / subfolder
        candidates.append(
            PathCandidate(
                path=roaming_pe,
                platform=PlatformType.WINDOWS,
                is_uwp=False,
                priority=20,
                exists=roaming_pe.exists(),
            )
        )

        local_pe = localappdata / "Minecraftpe" / "games" / "com.mojang" / subfolder
        candidates.append(
            PathCandidate(
                path=local_pe,
                platform=PlatformType.WINDOWS,
                is_uwp=False,
                priority=30,
                exists=local_pe.exists(),
            )
        )

        candidates.extend(cls._build_uwp_candidates(localappdata / "Packages", subfolder))

        home_bedrock = home_dir / ".minecraft" / "bedrock" / subfolder
        candidates.append(
            PathCandidate(
                path=home_bedrock,
                platform=PlatformType.WINDOWS,
                is_uwp=False,
                priority=80,
                exists=home_bedrock.exists(),
            )
        )

        return candidates

    @staticmethod
    def generate_darwin_candidates(home_dir: Path, subfolder: str) -> list[PathCandidate]:
        """Generate macOS candidate paths for Bedrock / MCPELauncher installations."""
        app_support = home_dir / "Library" / "Application Support"
        path1 = app_support / "mcpelauncher" / "games" / "com.mojang" / subfolder
        path2 = app_support / "minecraftpe" / "games" / "com.mojang" / subfolder
        return [
            PathCandidate(
                path=path1,
                platform=PlatformType.DARWIN,
                is_uwp=False,
                priority=10,
                exists=path1.exists(),
            ),
            PathCandidate(
                path=path2,
                platform=PlatformType.DARWIN,
                is_uwp=False,
                priority=20,
                exists=path2.exists(),
            ),
        ]

    @staticmethod
    def generate_linux_candidates(home_dir: Path, subfolder: str) -> list[PathCandidate]:
        """Generate Linux candidate paths for Bedrock / MCPELauncher installations."""
        local_share = home_dir / ".local" / "share"
        flatpak_root = home_dir / ".var" / "app" / "io.mrarm.mcpelauncher" / "data"
        path1 = local_share / "mcpelauncher" / "games" / "com.mojang" / subfolder
        path2 = local_share / "minecraftpe" / "games" / "com.mojang" / subfolder
        path3 = flatpak_root / "mcpelauncher" / "games" / "com.mojang" / subfolder
        return [
            PathCandidate(
                path=path1,
                platform=PlatformType.LINUX,
                is_uwp=False,
                priority=10,
                exists=path1.exists(),
            ),
            PathCandidate(
                path=path2,
                platform=PlatformType.LINUX,
                is_uwp=False,
                priority=20,
                exists=path2.exists(),
            ),
            PathCandidate(
                path=path3,
                platform=PlatformType.LINUX,
                is_uwp=False,
                priority=30,
                exists=path3.exists(),
            ),
        ]

    def _generate_candidates(
        self, plat: PlatformType, env: dict[str, str], home: Path, sub: str
    ) -> list[PathCandidate]:
        """Generate platform-specific search candidates."""
        if plat == PlatformType.WINDOWS:
            return self.generate_windows_candidates(env, home, sub)
        if plat == PlatformType.DARWIN:
            return self.generate_darwin_candidates(home, sub)
        if plat == PlatformType.LINUX:
            return self.generate_linux_candidates(home, sub)
        return []

    def _resolve_explicit_target(
        self, target: Path, auto_create: bool
    ) -> tuple[Optional[Path], list[str]]:
        """Attempt resolution and directory provisioning for an explicit target path."""
        warnings: list[str] = []
        resolved = target.resolve()
        if not resolved.exists() and auto_create:
            try:
                resolved.mkdir(parents=True, exist_ok=True)
            except OSError as err:
                warnings.append(f"Directory provisioning failed for {resolved}: {err}")
                return None, warnings
        return resolved, warnings

    def _probe_candidates(
        self, candidates: list[PathCandidate], auto_create: bool
    ) -> Optional[Path]:
        """Probe candidate paths and provision if feasible."""
        for candidate in candidates:
            if candidate.path.exists():
                return candidate.path.resolve()
            if candidate.path.parent.exists() and auto_create:
                try:
                    candidate.path.mkdir(parents=True, exist_ok=True)
                    return candidate.path.resolve()
                except OSError:
                    pass
        return None

    def _resolve_target_or_env(
        self, opts: ResolverOptions, subfolder: str, warnings: list[str]
    ) -> Optional[Path]:
        """Resolve custom destination or environment variable overrides."""
        if opts.custom_destination:
            resolved, warn = self._resolve_explicit_target(
                opts.custom_destination, opts.auto_create
            )
            warnings.extend(warn)
            if resolved:
                return resolved

        active_env = opts.env_vars if opts.env_vars is not None else dict(os.environ)
        env_override = active_env.get("MINECRAFT_DEVELOPMENT_PATH") or active_env.get(
            "BEDROCK_DEVELOPMENT_PATH"
        )
        if env_override:
            resolved, warn = self._resolve_explicit_target(
                Path(env_override) / subfolder, opts.auto_create
            )
            warnings.extend(warn)
            if resolved:
                return resolved
        return None

    def resolve_path(
        self, options: Optional[ResolverOptions] = None
    ) -> tuple[Path, bool, list[str]]:
        """Resolve absolute deployment path ensuring missing paths fall back gracefully."""
        opts = options or ResolverOptions()
        warnings: list[str] = []
        subfolder = self.get_subfolder_name(opts.pack_type)

        explicit = self._resolve_target_or_env(opts, subfolder, warnings)
        if explicit:
            return explicit, False, warnings

        active_env = opts.env_vars if opts.env_vars is not None else dict(os.environ)
        active_home = opts.home_dir.resolve() if opts.home_dir else Path.home().resolve()
        detected_plat = opts.platform_type or self.detect_platform()
        candidates = self._generate_candidates(detected_plat, active_env, active_home, subfolder)

        probed = self._probe_candidates(candidates, opts.auto_create)
        if probed:
            return probed, False, warnings

        if candidates and opts.auto_create:
            target_candidate = candidates[0].path.resolve()
            try:
                target_candidate.mkdir(parents=True, exist_ok=True)
                return target_candidate, False, warnings
            except OSError as err:
                warnings.append(f"Candidate directory creation failed: {err}")

        dist_root = opts.local_dist_root or Path("dist")
        fallback = (dist_root / subfolder).resolve()
        warnings.append(f"Target unresolved on {detected_plat.value}. Using local dist.")
        if opts.auto_create:
            fallback.mkdir(parents=True, exist_ok=True)
        return fallback, True, warnings
