"""Comprehensive test suite for Bedrock deployment path resolution and pack synchronization."""

import json
from pathlib import Path
import tempfile
import pytest

from packages.bedrock_deployment import (
    BedrockDeployer,
    BedrockPathResolver,
    DeploymentConfig,
    DeploymentResult,
    DeploymentValidator,
    PackType,
    PathCandidate,
    PlatformType,
    ResolverOptions,
    deploy_pack,
    resolve_bedrock_development_path,
)


def test_models_serialization():
    """Verify serialization of PathCandidate and DeploymentResult dataclasses."""
    target = Path("virtual/path")
    candidate = PathCandidate(
        path=target,
        platform=PlatformType.WINDOWS,
        is_uwp=True,
        priority=40,
        exists=False,
    )
    serialized_cand = candidate.as_dict()
    assert serialized_cand["path"] == str(target)
    assert serialized_cand["platform"] == "win32"
    assert serialized_cand["is_uwp"] is True
    assert serialized_cand["priority"] == 40
    assert serialized_cand["exists"] is False

    result = DeploymentResult(
        success=True,
        destination=target,
        files_copied=5,
        files_removed=2,
        fallback_used=False,
        warnings=["note"],
    )
    serialized_res = result.as_dict()
    assert serialized_res["success"] is True
    assert serialized_res["destination"] == str(target)
    assert serialized_res["files_copied"] == 5
    assert serialized_res["files_removed"] == 2
    assert serialized_res["warnings"] == ["note"]


def test_windows_candidate_generation_order(tmp_path):
    """Verify ordered Windows candidate paths prioritizing roaming then UWP packages."""
    env = {
        "APPDATA": str(tmp_path / "Roaming"),
        "LOCALAPPDATA": str(tmp_path / "Local"),
    }
    candidates = BedrockPathResolver.generate_windows_candidates(
        env, tmp_path, "development_behavior_packs"
    )
    assert len(candidates) >= 5
    assert ".minecraft" in str(candidates[0].path)
    assert candidates[0].is_uwp is False
    assert any(c.is_uwp for c in candidates)


def test_windows_uwp_path_resolution_when_exists(tmp_path):
    """Verify resolution prefers an existing UWP directory."""
    uwp_dir = (
        tmp_path
        / "Local"
        / "Packages"
        / "Microsoft.MinecraftUWP_8wekyb3d8bbwe"
        / "LocalState"
        / "games"
        / "com.mojang"
        / "development_behavior_packs"
    )
    uwp_dir.mkdir(parents=True, exist_ok=True)
    env = {
        "APPDATA": str(tmp_path / "Roaming"),
        "LOCALAPPDATA": str(tmp_path / "Local"),
    }
    resolver = BedrockPathResolver()
    opts = ResolverOptions(
        pack_type=PackType.BEHAVIOR,
        platform_type=PlatformType.WINDOWS,
        env_vars=env,
        home_dir=tmp_path,
        auto_create=True,
    )
    resolved, fallback, _ = resolver.resolve_path(opts)
    assert resolved == uwp_dir.resolve()
    assert fallback is False


def test_windows_roaming_path_resolution_when_exists(tmp_path):
    """Verify resolution picks roaming directory when present."""
    roaming_dir = tmp_path / "Roaming" / ".minecraft" / "bedrock" / "development_behavior_packs"
    roaming_dir.mkdir(parents=True, exist_ok=True)
    env = {
        "APPDATA": str(tmp_path / "Roaming"),
        "LOCALAPPDATA": str(tmp_path / "Local"),
    }
    resolver = BedrockPathResolver()
    opts = ResolverOptions(
        pack_type=PackType.BEHAVIOR,
        platform_type=PlatformType.WINDOWS,
        env_vars=env,
        home_dir=tmp_path,
        auto_create=True,
    )
    resolved, fallback, _ = resolver.resolve_path(opts)
    assert resolved == roaming_dir.resolve()
    assert fallback is False


def test_windows_prefers_existing_roaming_when_uwp_missing(tmp_path):
    """Verify roaming path is chosen when UWP path is missing on Windows 11."""
    roaming_pe = tmp_path / "Roaming" / "Minecraftpe" / "games" / "com.mojang" / "development_behavior_packs"
    roaming_pe.mkdir(parents=True, exist_ok=True)
    env = {
        "APPDATA": str(tmp_path / "Roaming"),
        "LOCALAPPDATA": str(tmp_path / "Local"),
    }
    resolver = BedrockPathResolver()
    opts = ResolverOptions(
        pack_type=PackType.BEHAVIOR,
        platform_type=PlatformType.WINDOWS,
        env_vars=env,
        home_dir=tmp_path,
        auto_create=True,
    )
    resolved, fallback, _ = resolver.resolve_path(opts)
    assert resolved == roaming_pe.resolve()
    assert fallback is False


def test_darwin_path_resolution(tmp_path):
    """Verify macOS candidate paths and resolution."""
    mac_dir = tmp_path / "Library" / "Application Support" / "mcpelauncher" / "games" / "com.mojang" / "development_behavior_packs"
    mac_dir.mkdir(parents=True, exist_ok=True)
    resolver = BedrockPathResolver()
    opts = ResolverOptions(
        pack_type=PackType.BEHAVIOR,
        platform_type=PlatformType.DARWIN,
        home_dir=tmp_path,
        auto_create=True,
    )
    resolved, fallback, _ = resolver.resolve_path(opts)
    assert resolved == mac_dir.resolve()
    assert fallback is False


def test_linux_path_resolution(tmp_path):
    """Verify Linux candidate paths and resolution."""
    linux_dir = tmp_path / ".local" / "share" / "mcpelauncher" / "games" / "com.mojang" / "development_behavior_packs"
    linux_dir.mkdir(parents=True, exist_ok=True)
    resolver = BedrockPathResolver()
    opts = ResolverOptions(
        pack_type=PackType.BEHAVIOR,
        platform_type=PlatformType.LINUX,
        home_dir=tmp_path,
        auto_create=True,
    )
    resolved, fallback, _ = resolver.resolve_path(opts)
    assert resolved == linux_dir.resolve()
    assert fallback is False


def test_missing_destination_auto_creation(tmp_path):
    """Verify graceful directory provisioning without throwing ENOENT exception."""
    missing = tmp_path / "deep" / "nested" / "development_behavior_packs"
    assert not missing.exists()
    resolver = BedrockPathResolver()
    opts = ResolverOptions(
        custom_destination=missing,
        auto_create=True,
    )
    resolved, fallback, _ = resolver.resolve_path(opts)
    assert resolved.exists()
    assert resolved == missing.resolve()
    assert fallback is False


def test_missing_destination_no_auto_create_fallback_to_dist(tmp_path):
    """Verify fallback when auto_create is False and candidate parent does not exist."""
    resolver = BedrockPathResolver()
    custom_dist = tmp_path / "build_output"
    opts = ResolverOptions(
        pack_type=PackType.BEHAVIOR,
        platform_type=PlatformType.UNKNOWN,
        auto_create=False,
        local_dist_root=custom_dist,
    )
    resolved, fallback, warnings = resolver.resolve_path(opts)
    assert fallback is True
    assert len(warnings) > 0
    assert str(custom_dist.resolve()) in str(resolved)


def test_environment_variable_override_minecraft_development_path(tmp_path):
    """Verify override using MINECRAFT_DEVELOPMENT_PATH environment variable."""
    env_root = tmp_path / "custom_bedrock_server"
    env = {"MINECRAFT_DEVELOPMENT_PATH": str(env_root)}
    resolver = BedrockPathResolver()
    opts = ResolverOptions(
        pack_type=PackType.BEHAVIOR,
        env_vars=env,
        auto_create=True,
    )
    resolved, fallback, _ = resolver.resolve_path(opts)
    assert resolved == (env_root / "development_behavior_packs").resolve()
    assert resolved.exists()
    assert fallback is False


def test_environment_variable_override_bedrock_development_path(tmp_path):
    """Verify override using BEDROCK_DEVELOPMENT_PATH environment variable."""
    env_root = tmp_path / "bedrock_env_workspace"
    env = {"BEDROCK_DEVELOPMENT_PATH": str(env_root)}
    resolver = BedrockPathResolver()
    opts = ResolverOptions(
        pack_type=PackType.BEHAVIOR,
        env_vars=env,
        auto_create=True,
    )
    resolved, fallback, _ = resolver.resolve_path(opts)
    assert resolved == (env_root / "development_behavior_packs").resolve()
    assert resolved.exists()
    assert fallback is False


def test_resource_pack_subfolder_resolution():
    """Verify correct subfolder selection for resource pack types."""
    resolver = BedrockPathResolver()
    assert resolver.get_subfolder_name(PackType.BEHAVIOR) == "development_behavior_packs"
    assert resolver.get_subfolder_name(PackType.RESOURCE) == "development_resource_packs"


def test_deployer_success_with_manifest_and_data(tmp_path):
    """Verify complete deployment lifecycle syncing manifest and assets."""
    source = tmp_path / "source_pack"
    target = tmp_path / "target_pack"
    source.mkdir()

    manifest = {
        "format_version": 2,
        "header": {
            "name": "Integration Pack",
            "uuid": "22222222-3333-4444-5555-666666666666",
            "version": [1, 0, 0],
        },
    }
    with (source / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle)

    (source / "script.js").write_text("console.log('test');", encoding="utf-8")

    deployer = BedrockDeployer()
    config = DeploymentConfig(
        source_dir=source,
        target_dir=target,
        auto_create=True,
        clean_slate=True,
    )
    result = deployer.deploy(config)
    assert result.success is True
    assert result.files_copied == 2
    assert result.files_removed == 0
    assert (target / "manifest.json").exists()
    assert (target / "script.js").exists()


def test_deployer_differential_sync_and_clean_slate(tmp_path):
    """Verify differential file hashing avoiding redundant copies and removing stale files."""
    source = tmp_path / "source_pack"
    target = tmp_path / "target_pack"
    source.mkdir()
    target.mkdir()

    (source / "file1.txt").write_text("same content", encoding="utf-8")
    (target / "file1.txt").write_text("same content", encoding="utf-8")
    (target / "orphan.txt").write_text("stale content", encoding="utf-8")

    manifest = {
        "format_version": 2,
        "header": {
            "name": "Diff Test Pack",
            "uuid": "33333333-4444-5555-6666-777777777777",
            "version": [1, 0, 0],
        },
    }
    with (source / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle)

    deployer = BedrockDeployer()
    config = DeploymentConfig(
        source_dir=source,
        target_dir=target,
        auto_create=True,
        clean_slate=True,
    )
    result = deployer.deploy(config)
    assert result.success is True
    assert result.files_copied == 1
    assert result.files_removed == 1
    assert not (target / "orphan.txt").exists()


def test_deployer_missing_source_failure(tmp_path):
    """Verify deployer gracefully fails when source directory is nonexistent."""
    missing_source = tmp_path / "non_existent_source"
    target = tmp_path / "target"
    config = DeploymentConfig(
        source_dir=missing_source,
        target_dir=target,
    )
    deployer = BedrockDeployer()
    result = deployer.deploy(config)
    assert result.success is False
    assert result.files_copied == 0
    assert "Source directory does not exist" in result.warnings


def test_validator_valid_manifest(tmp_path):
    """Verify validation of compliant manifest.json."""
    manifest = {
        "format_version": 2,
        "header": {
            "name": "Compliant Pack",
            "uuid": "44444444-5555-6666-7777-888888888888",
            "version": [1, 0, 0],
        },
    }
    with (tmp_path / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle)

    data = DeploymentValidator.validate_manifest(tmp_path)
    assert data["format_version"] == 2
    assert data["header"]["name"] == "Compliant Pack"


def test_validator_invalid_manifest_missing_format_version(tmp_path):
    """Verify validation failure when format_version is absent."""
    manifest = {
        "header": {
            "name": "Broken Pack",
            "uuid": "55555555-6666-7777-8888-999999999999",
        }
    }
    with (tmp_path / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle)

    with pytest.raises(ValueError, match="format_version"):
        DeploymentValidator.validate_manifest(tmp_path)


def test_validator_invalid_manifest_missing_header(tmp_path):
    """Verify validation failure when header is absent."""
    manifest = {"format_version": 2}
    with (tmp_path / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle)

    with pytest.raises(ValueError, match="header"):
        DeploymentValidator.validate_manifest(tmp_path)


def test_validator_safe_path(tmp_path):
    """Verify path safety verification rejects forbidden root directories."""
    forbidden = (tmp_path / "forbidden_root",)
    assert DeploymentValidator.validate_safe_path(tmp_path / "allowed", forbidden) is True
    assert DeploymentValidator.validate_safe_path(forbidden[0], forbidden) is False


def test_top_level_convenience_functions(tmp_path):
    """Verify top-level resolve_bedrock_development_path and deploy_pack."""
    source = tmp_path / "convenience_src"
    source.mkdir()
    manifest = {
        "format_version": 2,
        "header": {
            "name": "Convenience Pack",
            "uuid": "66666666-7777-8888-9999-000000000000",
            "version": [1, 0, 0],
        },
    }
    with (source / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle)

    target = tmp_path / "convenience_dst"
    result = deploy_pack(source, target)
    assert result.success is True

    resolved = resolve_bedrock_development_path(PackType.BEHAVIOR, custom_destination=target)
    assert resolved == target.resolve()
