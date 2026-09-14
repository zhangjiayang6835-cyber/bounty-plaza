"""Verification test harness for Bedrock deployment path resolution and pack synchronization."""

import json
from pathlib import Path
import sys
import tempfile

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


def verify_models() -> bool:
    """Validate data models, enums, and serialization routines."""
    dummy_path = Path("sample/path")
    candidate = PathCandidate(
        path=dummy_path,
        platform=PlatformType.WINDOWS,
        is_uwp=True,
        priority=10,
        exists=False,
    )
    cand_dict = candidate.as_dict()
    if cand_dict["is_uwp"] is not True:
        return False

    result = DeploymentResult(
        success=True,
        destination=dummy_path,
        files_copied=3,
        files_removed=1,
        fallback_used=False,
    )
    res_dict = result.as_dict()
    return bool(res_dict["success"] and res_dict["files_copied"] == 3)


def verify_windows_candidates() -> bool:
    """Validate generation of modern Windows roaming and UWP candidate paths."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_base = Path(tmp_dir).resolve()
        env = {
            "APPDATA": str(tmp_base / "Roaming"),
            "LOCALAPPDATA": str(tmp_base / "Local"),
        }
        candidates = BedrockPathResolver.generate_windows_candidates(
            env, tmp_base, "development_behavior_packs"
        )
        has_uwp = any(c.is_uwp for c in candidates)
        has_roaming = any(".minecraft" in str(c.path) for c in candidates)
        return bool(len(candidates) >= 4 and has_uwp and has_roaming)


def verify_path_resolution_with_existing_uwp() -> bool:
    """Verify that existing UWP destination is resolved accurately."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_base = Path(tmp_dir).resolve()
        uwp_target = (
            tmp_base
            / "Local"
            / "Packages"
            / "Microsoft.MinecraftUWP_8wekyb3d8bbwe"
            / "LocalState"
            / "games"
            / "com.mojang"
            / "development_behavior_packs"
        )
        uwp_target.mkdir(parents=True, exist_ok=True)
        env = {
            "APPDATA": str(tmp_base / "Roaming"),
            "LOCALAPPDATA": str(tmp_base / "Local"),
        }
        resolver = BedrockPathResolver()
        opts = ResolverOptions(
            pack_type=PackType.BEHAVIOR,
            platform_type=PlatformType.WINDOWS,
            env_vars=env,
            home_dir=tmp_base,
            auto_create=True,
        )
        resolved, fallback, _ = resolver.resolve_path(opts)
        return bool(resolved == uwp_target and not fallback)


def verify_path_resolution_with_roaming_fallback() -> bool:
    """Verify that existing Roaming destination is resolved when UWP is absent."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_base = Path(tmp_dir).resolve()
        roaming_target = (
            tmp_base / "Roaming" / ".minecraft" / "bedrock" / "development_behavior_packs"
        )
        roaming_target.mkdir(parents=True, exist_ok=True)
        env = {
            "APPDATA": str(tmp_base / "Roaming"),
            "LOCALAPPDATA": str(tmp_base / "Local"),
        }
        resolver = BedrockPathResolver()
        opts = ResolverOptions(
            pack_type=PackType.BEHAVIOR,
            platform_type=PlatformType.WINDOWS,
            env_vars=env,
            home_dir=tmp_base,
            auto_create=True,
        )
        resolved, fallback, _ = resolver.resolve_path(opts)
        return bool(resolved == roaming_target and not fallback)


def verify_missing_destination_auto_creation() -> bool:
    """Verify graceful directory provisioning without throwing ENOENT exceptions."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_base = Path(tmp_dir).resolve()
        missing_dest = tmp_base / "provision_test" / "development_behavior_packs"
        resolver = BedrockPathResolver()
        opts = ResolverOptions(
            custom_destination=missing_dest,
            auto_create=True,
        )
        resolved, fallback, _ = resolver.resolve_path(opts)
        return bool(resolved.exists() and not fallback)


def verify_environment_variable_override() -> bool:
    """Verify explicit override via MINECRAFT_DEVELOPMENT_PATH environment variable."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_base = Path(tmp_dir).resolve()
        env = {"MINECRAFT_DEVELOPMENT_PATH": str(tmp_base / "custom_env_root")}
        resolver = BedrockPathResolver()
        opts = ResolverOptions(
            pack_type=PackType.RESOURCE,
            env_vars=env,
            auto_create=True,
        )
        resolved, fallback, _ = resolver.resolve_path(opts)
        expected = tmp_base / "custom_env_root" / "development_resource_packs"
        return bool(resolved == expected and resolved.exists() and not fallback)


def verify_validator_logic() -> bool:
    """Verify manifest schema validation and path safety rules."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_base = Path(tmp_dir).resolve()
        valid_manifest = {
            "format_version": 2,
            "header": {
                "name": "Validation Test Pack",
                "uuid": "11111111-2222-3333-4444-555555555555",
                "version": [1, 0, 0],
            },
        }
        manifest_file = tmp_base / "manifest.json"
        with manifest_file.open("w", encoding="utf-8") as handle:
            json.dump(valid_manifest, handle)

        data = DeploymentValidator.validate_manifest(tmp_base)
        safe = DeploymentValidator.validate_safe_path(tmp_base)
        writable = DeploymentValidator.is_writable(tmp_base)
        return bool(data["format_version"] == 2 and safe and writable)


def verify_deployer_execution() -> bool:
    """Verify end-to-end pack synchronization, file diffing, and cleanup."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_base = Path(tmp_dir).resolve()
        source = tmp_base / "source_pack"
        target = tmp_base / "target_dir"
        source.mkdir()

        manifest = {
            "format_version": 2,
            "header": {
                "name": "Deployer Test Pack",
                "uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "version": [1, 0, 0],
            },
        }
        with (source / "manifest.json").open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle)

        (source / "data.txt").write_text("initial payload", encoding="utf-8")
        target.mkdir()
        (target / "obsolete.txt").write_text("old file", encoding="utf-8")

        config = DeploymentConfig(
            source_dir=source,
            target_dir=target,
            auto_create=True,
            clean_slate=True,
        )
        deployer = BedrockDeployer()
        res1 = deployer.deploy(config)
        first_pass_ok = (
            res1.success
            and res1.files_copied == 2
            and res1.files_removed == 1
            and not (target / "obsolete.txt").exists()
        )

        res2 = deployer.deploy(config)
        second_pass_ok = res2.success and res2.files_copied == 0

        return bool(first_pass_ok and second_pass_ok)


def verify_top_level_helpers() -> bool:
    """Verify module level entrypoint functions."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_base = Path(tmp_dir).resolve()
        source = tmp_base / "source"
        source.mkdir()
        manifest = {
            "format_version": 2,
            "header": {
                "name": "Helper Pack",
                "uuid": "99999999-8888-7777-6666-555555555555",
                "version": [1, 0, 0],
            },
        }
        with (source / "manifest.json").open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle)

        target = tmp_base / "helper_target"
        res = deploy_pack(source, target)
        path = resolve_bedrock_development_path(
            PackType.BEHAVIOR, custom_destination=target
        )
        return bool(res.success and path == target)


def run_all_verifications() -> bool:
    """Execute all verification stages and return overall success status."""
    stages = [
        ("Models", verify_models),
        ("Windows Candidates", verify_windows_candidates),
        ("UWP Path Resolution", verify_path_resolution_with_existing_uwp),
        ("Roaming Fallback", verify_path_resolution_with_roaming_fallback),
        ("Auto Provisioning", verify_missing_destination_auto_creation),
        ("Env Override", verify_environment_variable_override),
        ("Validator", verify_validator_logic),
        ("Deployer Execution", verify_deployer_execution),
        ("Top-Level Helpers", verify_top_level_helpers),
    ]

    all_passed = True
    for name, func in stages:
        passed = func()
        status_label = "PASS" if passed else "FAIL"
        print(f"[{status_label}] {name}")
        if not passed:
            all_passed = False

    return all_passed


if __name__ == "__main__":
    if run_all_verifications():
        print("Verification complete: all checks passed.")
        sys.exit(0)
    print("Verification failed: one or more checks encountered errors.")
    sys.exit(1)
