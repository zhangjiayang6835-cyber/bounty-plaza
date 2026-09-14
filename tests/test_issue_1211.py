"""Unit and integration tests for Issue #1211 Bedrock development pack resolver."""

from pathlib import Path
import pytest

from packages.bedrock_pack_resolver.cli import main as cli_main
from packages.bedrock_pack_resolver.models import (
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
)


def make_package_mojang_dir(local_app_data: Path, package_name: str) -> Path:
    """Create a mock package directory structure for testing.

    Args:
        local_app_data: Path to Local AppData.
        package_name: Package directory name to create.

    Returns:
        Path to the created com.mojang directory.
    """
    mojang_dir = (
        local_app_data
        / "Packages"
        / package_name
        / "LocalState"
        / "games"
        / "com.mojang"
    )
    mojang_dir.mkdir(parents=True)
    return mojang_dir


def test_legacy_uwp_resolution(tmp_path: Path) -> None:
    """Verify legacy UWP package directory resolution."""
    local_app_data = tmp_path / "AppData" / "Local"
    mojang_dir = make_package_mojang_dir(
        local_app_data, "Microsoft.MinecraftUWP_8wekyb3d8bbwe"
    )
    expected_packs = mojang_dir / "development_behavior_packs"
    expected_packs.mkdir(parents=True)

    opts = BedrockResolverOptions(local_app_data=str(local_app_data))
    resolved = get_development_packs_path(opts)
    assert resolved == str(expected_packs)


def test_modern_windows_store_resolution(tmp_path: Path) -> None:
    """Verify modern retail Windows Store package detection."""
    local_app_data = tmp_path / "AppData" / "Local"
    mojang_dir = make_package_mojang_dir(
        local_app_data, "Microsoft.MinecraftWindows_8wekyb3d8bbwe"
    )
    expected_packs = mojang_dir / "development_behavior_packs"
    expected_packs.mkdir(parents=True)

    opts = BedrockResolverOptions(local_app_data=str(local_app_data))
    resolved = get_development_packs_path(opts)
    assert resolved == str(expected_packs)


def test_windows_app_installer_resolution(tmp_path: Path) -> None:
    """Verify Windows App Installer (MAPI) package detection."""
    local_app_data = tmp_path / "AppData" / "Local"
    mojang_dir = make_package_mojang_dir(
        local_app_data, "Minecraft.Windows_8wekyb3d8bbwe"
    )
    expected_packs = mojang_dir / "development_behavior_packs"
    expected_packs.mkdir(parents=True)

    opts = BedrockResolverOptions(local_app_data=str(local_app_data))
    resolved = get_development_packs_path(opts)
    assert resolved == str(expected_packs)


def test_beta_preview_resolution(tmp_path: Path) -> None:
    """Verify Bedrock Preview and Beta package detection."""
    local_app_data = tmp_path / "AppData" / "Local"
    mojang_dir = make_package_mojang_dir(
        local_app_data, "Microsoft.MinecraftWindowsBeta_8wekyb3d8bbwe"
    )
    expected_packs = mojang_dir / "development_behavior_packs"
    expected_packs.mkdir(parents=True)

    opts = BedrockResolverOptions(local_app_data=str(local_app_data))
    resolved = get_development_packs_path(opts)
    assert resolved == str(expected_packs)


def test_education_edition_resolution(tmp_path: Path) -> None:
    """Verify Bedrock Education Edition package detection."""
    local_app_data = tmp_path / "AppData" / "Local"
    mojang_dir = make_package_mojang_dir(
        local_app_data, "Microsoft.MinecraftEducationEdition_8wekyb3d8bbwe"
    )
    expected_packs = mojang_dir / "development_behavior_packs"
    expected_packs.mkdir(parents=True)

    opts = BedrockResolverOptions(local_app_data=str(local_app_data))
    resolved = get_development_packs_path(opts)
    assert resolved == str(expected_packs)


def test_dynamic_package_discovery(tmp_path: Path) -> None:
    """Verify dynamic discovery of custom Minecraft package name."""
    local_app_data = tmp_path / "AppData" / "Local"
    packages_dir = local_app_data / "Packages"
    custom_pkg = packages_dir / "Microsoft.MinecraftCustomBuild_xyz123"
    mojang_dir = custom_pkg / "LocalState" / "games" / "com.mojang"
    expected_packs = mojang_dir / "development_behavior_packs"
    expected_packs.mkdir(parents=True)

    found_dir = find_minecraft_package_dir(str(packages_dir))
    assert found_dir == str(custom_pkg)

    opts = BedrockResolverOptions(local_app_data=str(local_app_data))
    resolved = get_development_packs_path(opts)
    assert resolved == str(expected_packs)


def test_standalone_launcher_local_app_data(tmp_path: Path) -> None:
    """Verify standalone non-packaged launcher path in LocalAppData."""
    local_app_data = tmp_path / "AppData" / "Local"
    mojang_dir = local_app_data / "Minecraft" / "LocalState" / "games" / "com.mojang"
    expected_packs = mojang_dir / "development_behavior_packs"
    expected_packs.mkdir(parents=True)

    opts = BedrockResolverOptions(local_app_data=str(local_app_data))
    resolved = get_development_packs_path(opts)
    assert resolved == str(expected_packs)


def test_standalone_launcher_bedrock_folder(tmp_path: Path) -> None:
    """Verify standalone launcher path in LocalAppData/Minecraft Bedrock."""
    local_app_data = tmp_path / "AppData" / "Local"
    mojang_dir = (
        local_app_data / "Minecraft Bedrock" / "LocalState" / "games" / "com.mojang"
    )
    expected_packs = mojang_dir / "development_behavior_packs"
    expected_packs.mkdir(parents=True)

    opts = BedrockResolverOptions(local_app_data=str(local_app_data))
    resolved = get_development_packs_path(opts)
    assert resolved == str(expected_packs)


def test_standalone_launcher_roaming_app_data(tmp_path: Path) -> None:
    """Verify standalone launcher fallback in Roaming AppData."""
    local_app_data = tmp_path / "AppData" / "Local"
    roaming_app_data = tmp_path / "AppData" / "Roaming"
    mojang_dir = roaming_app_data / "Minecraft Bedrock" / "games" / "com.mojang"
    expected_packs = mojang_dir / "development_behavior_packs"
    expected_packs.mkdir(parents=True)

    opts = BedrockResolverOptions(
        local_app_data=str(local_app_data),
        app_data=str(roaming_app_data),
    )
    resolved = get_development_packs_path(opts)
    assert resolved == str(expected_packs)


def test_direct_env_override(tmp_path: Path) -> None:
    """Verify direct MINECRAFT_DEV_PACKS_PATH override takes precedence."""
    custom_target = tmp_path / "direct_override_packs"
    custom_target.mkdir(parents=True)

    opts = BedrockResolverOptions(
        custom_env={"MINECRAFT_DEV_PACKS_PATH": str(custom_target)},
    )
    resolved = get_development_packs_path(opts)
    assert resolved == str(custom_target)


def test_bedrock_base_env_override(tmp_path: Path) -> None:
    """Verify MINECRAFT_BEDROCK_PATH base directory override."""
    base_dir = tmp_path / "custom_bedrock"
    mojang_dir = base_dir / "games" / "com.mojang"
    expected_packs = mojang_dir / "development_behavior_packs"
    mojang_dir.mkdir(parents=True)

    opts = BedrockResolverOptions(
        custom_env={"MINECRAFT_BEDROCK_PATH": str(base_dir)},
    )
    resolved = get_development_packs_path(opts)
    assert resolved == str(expected_packs)


def test_auto_creation_without_admin(tmp_path: Path) -> None:
    """Verify directory is created automatically if com.mojang exists."""
    local_app_data = tmp_path / "AppData" / "Local"
    mojang_dir = make_package_mojang_dir(
        local_app_data, "Microsoft.MinecraftWindows_8wekyb3d8bbwe"
    )

    expected_packs = mojang_dir / "development_behavior_packs"
    assert not expected_packs.exists()

    opts = BedrockResolverOptions(
        local_app_data=str(local_app_data),
        auto_create=True,
    )
    resolved = get_development_packs_path(opts)
    assert resolved == str(expected_packs)
    assert expected_packs.exists()


def test_auto_create_disabled_raises_error(tmp_path: Path) -> None:
    """Verify FileNotFoundError is raised when auto_create is False and pack folder missing."""
    local_app_data = tmp_path / "AppData" / "Local"
    make_package_mojang_dir(local_app_data, "Microsoft.MinecraftWindows_8wekyb3d8bbwe")

    opts = BedrockResolverOptions(
        local_app_data=str(local_app_data),
        auto_create=False,
    )
    with pytest.raises(FileNotFoundError) as exc_info:
        get_development_packs_path(opts)
    assert "ENOENT: no such file or directory" in str(exc_info.value)


def test_resource_pack_type(tmp_path: Path) -> None:
    """Verify resolution of development_resource_packs."""
    local_app_data = tmp_path / "AppData" / "Local"
    mojang_dir = make_package_mojang_dir(
        local_app_data, "Microsoft.MinecraftWindows_8wekyb3d8bbwe"
    )

    opts = BedrockResolverOptions(
        local_app_data=str(local_app_data),
        pack_type=PackType.RESOURCE,
    )
    resolved = get_development_packs_path(opts)
    expected = mojang_dir / "development_resource_packs"
    assert resolved == str(expected)
    assert expected.exists()


def test_skin_pack_type(tmp_path: Path) -> None:
    """Verify resolution of development_skin_packs."""
    local_app_data = tmp_path / "AppData" / "Local"
    mojang_dir = make_package_mojang_dir(
        local_app_data, "Microsoft.MinecraftWindows_8wekyb3d8bbwe"
    )

    opts = BedrockResolverOptions(
        local_app_data=str(local_app_data),
        pack_type=PackType.SKIN,
    )
    resolved = get_development_packs_path(opts)
    expected = mojang_dir / "development_skin_packs"
    assert resolved == str(expected)
    assert expected.exists()


def test_missing_installation_raises_not_found(tmp_path: Path) -> None:
    """Verify BedrockPathNotFoundError is raised when no directory exists."""
    empty_local = tmp_path / "empty_dir"
    empty_local.mkdir(parents=True)

    opts = BedrockResolverOptions(local_app_data=str(empty_local))
    with pytest.raises(BedrockPathNotFoundError) as exc_info:
        get_development_packs_path(opts)

    err = exc_info.value
    assert "ENOENT: no such file or directory" in str(err)
    assert len(err.candidates) > 0


def test_list_candidate_paths(tmp_path: Path) -> None:
    """Verify candidate inspection returns expected search path order."""
    local_app_data = tmp_path / "AppData" / "Local"
    opts = BedrockResolverOptions(local_app_data=str(local_app_data))
    candidates = list_candidate_mojang_paths(opts)

    assert any("Microsoft.MinecraftWindows_8wekyb3d8bbwe" in p for p in candidates)
    assert any("Microsoft.MinecraftUWP_8wekyb3d8bbwe" in p for p in candidates)
    assert any("Minecraft.Windows_8wekyb3d8bbwe" in p for p in candidates)


def test_resolve_dev_packs_alias(tmp_path: Path) -> None:
    """Verify resolve_dev_packs alias functions identically."""
    local_app_data = tmp_path / "AppData" / "Local"
    mojang_dir = make_package_mojang_dir(
        local_app_data, "Microsoft.MinecraftWindows_8wekyb3d8bbwe"
    )

    opts = BedrockResolverOptions(local_app_data=str(local_app_data))
    resolved = resolve_dev_packs(opts)
    assert resolved == str(mojang_dir / "development_behavior_packs")


def test_get_mojang_base_path(tmp_path: Path) -> None:
    """Verify get_mojang_base_path returns the com.mojang directory."""
    local_app_data = tmp_path / "AppData" / "Local"
    mojang_dir = make_package_mojang_dir(
        local_app_data, "Microsoft.MinecraftWindows_8wekyb3d8bbwe"
    )

    opts = BedrockResolverOptions(local_app_data=str(local_app_data))
    base = get_mojang_base_path(opts)
    assert base == str(mojang_dir)


def test_cli_list_candidates(capsys) -> None:
    """Verify CLI list candidates command executes successfully."""
    exit_code = cli_main(["--list-candidates", "--json"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"candidates":' in captured.out


def test_cli_resolution_success(tmp_path: Path, capsys) -> None:
    """Verify CLI resolves path when directory exists."""
    local_app_data = tmp_path / "AppData" / "Local"
    make_package_mojang_dir(local_app_data, "Microsoft.MinecraftWindows_8wekyb3d8bbwe")

    exit_code = cli_main(["--localappdata", str(local_app_data), "--json"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"status": "success"' in captured.out
    assert "development_behavior_packs" in captured.out


def test_cli_resolution_failure(tmp_path: Path, capsys) -> None:
    """Verify CLI reports failure JSON when no Minecraft install is present."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir(parents=True)

    exit_code = cli_main(["--localappdata", str(empty_dir), "--json"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert '"status": "failed"' in captured.out
