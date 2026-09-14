"""Bedrock pack deployment engine and cross-platform path resolution architecture."""

from pathlib import Path
from typing import Optional

from .deployer import BedrockDeployer
from .models import (
    DeploymentConfig,
    DeploymentResult,
    PackType,
    PathCandidate,
    PlatformType,
)
from .resolver import BedrockPathResolver, ResolverOptions
from .validator import DeploymentValidator

__all__ = [
    "BedrockDeployer",
    "BedrockPathResolver",
    "DeploymentConfig",
    "DeploymentResult",
    "DeploymentValidator",
    "PackType",
    "PathCandidate",
    "PlatformType",
    "ResolverOptions",
    "deploy_pack",
    "resolve_bedrock_development_path",
]


def resolve_bedrock_development_path(
    pack_type: PackType = PackType.BEHAVIOR,
    custom_destination: Optional[Path] = None,
    platform_override: Optional[str] = None,
) -> Path:
    """Resolve Bedrock development destination path with graceful directory fallback."""
    resolver = BedrockPathResolver()
    plat = (
        BedrockPathResolver.detect_platform(platform_override) if platform_override else None
    )
    opts = ResolverOptions(
        pack_type=pack_type,
        custom_destination=custom_destination,
        platform_type=plat,
    )
    path, _, _ = resolver.resolve_path(opts)
    return path


def deploy_pack(
    source_dir: Path,
    target_dir: Optional[Path] = None,
    pack_type: PackType = PackType.BEHAVIOR,
    dry_run: bool = False,
) -> DeploymentResult:
    """Deploy Bedrock pack to target development folder safely."""
    deployer = BedrockDeployer()
    config = DeploymentConfig(
        source_dir=source_dir,
        target_dir=target_dir,
        pack_type=pack_type,
        dry_run=dry_run,
    )
    return deployer.deploy(config)
