"""Comprehensive unit test suite for Bedrock Custom Slash Commands (#1323)."""

from pathlib import Path
import pytest

from packages.bedrock_custom_slash_commands import (
    BedrockCommandRegistry,
    CommandDefinitionValidator,
    CommandMigrationPipeline,
    CommandPermissionLevel,
    CustomCommandDefinition,
    CustomCommandOrigin,
    CustomCommandParameter,
    CustomCommandParamType,
    CustomCommandStatus,
    InspectCommandService,
    LifecyclePhase,
    ScriptCommandAstValidator,
)


def test_models_and_serialization() -> None:
    """Verify data model serialization and deserialization properties."""
    param = CustomCommandParameter(
        name="target",
        param_type=CustomCommandParamType.STRING,
        optional=True,
    )
    definition = CustomCommandDefinition(
        name="engine:inspect",
        description="Inspect administrative engine status and entity metrics.",
        permission_level=CommandPermissionLevel.ADMIN,
        mandatory_parameters=[],
        optional_parameters=[param],
    )

    data = definition.to_dict()
    restored = CustomCommandDefinition.from_dict(data)

    assert definition.has_namespace is True
    assert definition.namespace == "engine"
    assert definition.command_name == "inspect"
    assert restored.name == definition.name
    assert restored.permission_level == CommandPermissionLevel.ADMIN
    assert len(restored.optional_parameters) == 1
    assert restored.optional_parameters[0].name == "target"


def test_bug_reproduction_static_registry_call_flagged() -> None:
    """Verify AST validator detects static CustomCommandRegistry.registerCommand calls."""
    buggy_snippet = (
        "import { CustomCommandRegistry, CommandPermissionLevel } from '@minecraft/server';\n"
        "export function registerInspectCommand() {\n"
        "  CustomCommandRegistry.registerCommand('inspect', () => {});\n"
        "}\n"
    )
    validator = ScriptCommandAstValidator()
    report = validator.validate_script_content(buggy_snippet)

    assert report.is_valid is False
    assert report.has_code("STATIC_REGISTRY_INVOCATION_DETECTED") is True


def test_script_ast_validation_passes_on_fixed_code() -> None:
    """Verify that scripts/commands/inspect.ts passes all static analysis rules."""
    inspect_ts_path = Path("scripts/commands/inspect.ts")
    assert inspect_ts_path.is_file()

    validator = ScriptCommandAstValidator()
    report = validator.validate_script_file(str(inspect_ts_path))

    assert report.is_valid is True
    assert report.has_code("STATIC_REGISTRY_INVOCATION_DETECTED") is False
    assert report.has_code("CHAT_SEND_DEPRECATED_DETECTED") is False
    assert report.has_code("TICK_LOOP_REGISTRATION_DETECTED") is False


def test_registry_lifecycle_enforcement() -> None:
    """Verify registration fails outside STARTUP lifecycle phase."""
    registry = BedrockCommandRegistry()
    assert registry.phase == LifecyclePhase.PRE_STARTUP

    cmd_def = CustomCommandDefinition(
        name="inspect",
        description="Inspect state.",
        permission_level=CommandPermissionLevel.ADMIN,
    )

    with pytest.raises(RuntimeError, match="before startup event begins"):
        registry.register_command(cmd_def)

    registry.start_lifecycle()
    assert registry.phase == LifecyclePhase.STARTUP
    registry.register_command(cmd_def)

    registry.complete_startup()
    assert registry.phase == LifecyclePhase.RUNNING

    with pytest.raises(RuntimeError, match="after startup lifecycle ended"):
        registry.register_command(cmd_def)


def test_registry_execution_and_permission_gating() -> None:
    """Verify permission gating blocks unauthorized users and permits admins."""
    registry = BedrockCommandRegistry()
    registry.start_lifecycle()

    InspectCommandService.register_inspect_command(registry)
    registry.complete_startup()

    assert "inspect" in registry.registered_commands()
    assert "engine:inspect" in registry.registered_commands()

    unauthorized_origin = CustomCommandOrigin(
        source_type="player",
        source_name="RegularPlayer",
        permission_level=CommandPermissionLevel.NORMAL,
    )
    blocked_result = registry.execute_command("inspect", unauthorized_origin)
    assert blocked_result.status == CustomCommandStatus.FAILURE
    assert "Permission denied" in (blocked_result.message or "")

    admin_origin = CustomCommandOrigin(
        source_type="player",
        source_name="AdminPlayer",
        source_entity_id="uuid-admin-1",
        location=(100.0, 64.0, 200.0),
        permission_level=CommandPermissionLevel.ADMIN,
    )
    allowed_result = registry.execute_command("inspect", admin_origin)
    assert allowed_result.status == CustomCommandStatus.SUCCESS
    assert "Inspected entity 'uuid-admin-1'" in (allowed_result.message or "")


def test_inspect_service_entity_inspection() -> None:
    """Verify entity inspection telemetry report and formatting."""
    origin = CustomCommandOrigin(
        source_type="entity",
        source_name="Zombie",
        source_entity_id="entity-zombie-9",
        location=(10.5, 70.0, -15.2),
        permission_level=CommandPermissionLevel.ADMIN,
    )
    result = InspectCommandService.execute_inspect(origin)

    assert result.status == CustomCommandStatus.SUCCESS
    assert "Inspected entity 'entity-zombie-9'" in (result.message or "")
    assert "10.5, 70.0, -15.2" in (result.message or "")


def test_inspect_service_block_inspection() -> None:
    """Verify command block inspection."""
    origin = CustomCommandOrigin(
        source_type="block",
        location=(0.0, 10.0, 0.0),
        permission_level=CommandPermissionLevel.ADMIN,
    )
    result = InspectCommandService.execute_inspect(origin)

    assert result.status == CustomCommandStatus.SUCCESS
    assert "Inspected command block at [0.0, 10.0, 0.0]" in (result.message or "")


def test_inspect_service_server_console() -> None:
    """Verify server console inspection telemetry."""
    origin = CustomCommandOrigin(
        source_type="server",
        permission_level=CommandPermissionLevel.ADMIN,
    )
    result = InspectCommandService.execute_inspect(origin)

    assert result.status == CustomCommandStatus.SUCCESS
    assert "BDS Server Console inspected" in (result.message or "")
    assert "Subsystems operational" in (result.message or "")


def test_command_definition_validator_rules() -> None:
    """Verify validator flags leading slashes and insecure admin permissions."""
    validator = CommandDefinitionValidator()

    slash_cmd = CustomCommandDefinition(
        name="/inspect",
        description="Inspect command",
        permission_level=CommandPermissionLevel.ADMIN,
    )
    slash_report = validator.validate_definition(slash_cmd)
    assert slash_report.is_valid is False
    assert slash_report.has_code("LEADING_SLASH_DETECTED") is True

    insecure_admin = CustomCommandDefinition(
        name="admin:inspect",
        description="Admin inspect",
        permission_level=CommandPermissionLevel.ANY,
    )
    insecure_report = validator.validate_definition(insecure_admin)
    assert insecure_report.is_valid is False
    assert insecure_report.has_code("INSECURE_ADMIN_PERMISSION") is True


def test_migration_pipeline() -> None:
    """Verify migration pipeline rewrites static registry calls to event registry calls."""
    pipeline = CommandMigrationPipeline()
    legacy_code = (
        "function register() {\n"
        "  CustomCommandRegistry.registerCommand('inspect', { desc: 'test' });\n"
        "}\n"
    )
    migrated = pipeline.migrate_script_content(legacy_code)

    assert "CustomCommandRegistry.registerCommand" not in migrated
    assert "event.customCommandRegistry.registerCommand" in migrated
