"""Unit and integration test suite for Bedrock custom slash commands (#1208)."""

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
    CustomCommandResult,
    CustomCommandStatus,
    LifecyclePhase,
    ScriptCommandAstValidator,
)


def test_command_parameter_serialization() -> None:
    """Validate parameter creation, serialization, and deserialization."""
    param = CustomCommandParameter(
        name="target_player",
        param_type=CustomCommandParamType.STRING,
        optional=False,
    )
    serialized = param.to_dict()
    assert serialized["name"] == "target_player"
    assert serialized["type"] == "String"
    assert not serialized["optional"]

    restored = CustomCommandParameter.from_dict(serialized)
    assert restored.name == param.name
    assert restored.param_type == param.param_type
    assert restored.optional == param.optional


def test_command_definition_properties() -> None:
    """Verify namespace extraction and dictionary roundtrip for command definitions."""
    target_param = CustomCommandParameter(
        name="target",
        param_type=CustomCommandParamType.STRING,
    )
    mode_param = CustomCommandParameter(
        name="mode",
        param_type=CustomCommandParamType.ENUM,
        enum_name="InspectMode",
        optional=True,
    )
    definition = CustomCommandDefinition(
        name="admin:inspect",
        description="Inspect player inventory and state.",
        permission_level=CommandPermissionLevel.GAME_DIRECTORS,
        cheats_required=False,
        mandatory_parameters=[target_param],
        optional_parameters=[mode_param],
    )

    assert definition.has_namespace
    assert definition.namespace == "admin"
    assert definition.command_name == "inspect"

    data = definition.to_dict()
    assert data["name"] == "admin:inspect"
    assert data["permissionLevel"] == 1

    restored = CustomCommandDefinition.from_dict(data)
    assert restored.name == definition.name
    assert restored.permission_level == CommandPermissionLevel.GAME_DIRECTORS
    assert len(restored.mandatory_parameters) == 1
    assert len(restored.optional_parameters) == 1
    assert restored.optional_parameters[0].enum_name == "InspectMode"


def test_command_definition_validator_success() -> None:
    """Ensure valid command definition passes all validation rules."""
    validator = CommandDefinitionValidator()
    definition = CustomCommandDefinition(
        name="admin:inspect",
        description="Inspect player inventory, state, and permissions.",
        permission_level=CommandPermissionLevel.GAME_DIRECTORS,
        mandatory_parameters=[
            CustomCommandParameter(name="target", param_type=CustomCommandParamType.STRING)
        ],
    )
    report = validator.validate_definition(definition)
    assert report.is_valid
    assert len(report.errors) == 0


def test_command_definition_validator_rejections() -> None:
    """Verify validator flags leading slashes, missing namespaces, and insecure permissions."""
    validator = CommandDefinitionValidator()

    leading_slash = CustomCommandDefinition(
        name="/inspect",
        description="Invalid leading slash.",
        permission_level=CommandPermissionLevel.GAME_DIRECTORS,
    )
    report_slash = validator.validate_definition(leading_slash)
    assert not report_slash.is_valid
    assert report_slash.has_code("LEADING_SLASH_DETECTED")
    assert report_slash.has_code("MISSING_COMMAND_NAMESPACE")

    insecure_admin = CustomCommandDefinition(
        name="admin:inspect",
        description="Administrative inspect with insecure permission.",
        permission_level=CommandPermissionLevel.ANY,
    )
    report_insecure = validator.validate_definition(insecure_admin)
    assert not report_insecure.is_valid
    assert report_insecure.has_code("INSECURE_ADMIN_PERMISSION")

    missing_enum = CustomCommandDefinition(
        name="custom:filter",
        description="Filter items by category enum.",
        permission_level=CommandPermissionLevel.ANY,
        mandatory_parameters=[
            CustomCommandParameter(name="category", param_type=CustomCommandParamType.ENUM)
        ],
    )
    report_enum = validator.validate_definition(missing_enum)
    assert not report_enum.is_valid
    assert report_enum.has_code("MISSING_ENUM_NAME")


def test_script_ast_validator_detects_legacy_antipatterns() -> None:
    """Verify AST validator identifies deprecated chatSend and tick-loop registrations."""
    validator = ScriptCommandAstValidator()
    legacy_code = (
        "import { world, system } from '@minecraft/server';\n"
        "export function registerCustomCommands() {\n"
        "  system.runInterval(() => {\n"
        "    world.beforeEvents.chatSend.subscribe((event) => {\n"
        "      if (event.message.startsWith('/inspect')) {\n"
        "        event.cancel = true;\n"
        "      }\n"
        "    });\n"
        "  });\n"
        "}\n"
    )

    report = validator.validate_script_content(legacy_code)
    assert not report.is_valid
    assert report.has_code("CHAT_SEND_DEPRECATED_DETECTED")
    assert report.has_code("TICK_LOOP_REGISTRATION_DETECTED")
    assert report.has_code("MISSING_STARTUP_LIFECYCLE")
    assert report.has_code("MISSING_PERMISSION_ENUM_IMPORT")


def test_script_ast_validator_approves_modern_commands_ts() -> None:
    """Verify scripts/commands.ts adheres to Bedrock lifecycle and security invariants."""
    validator = ScriptCommandAstValidator()
    script_path = Path("scripts/commands.ts")
    assert script_path.is_file()

    report = validator.validate_script_file(str(script_path))
    assert report.is_valid
    assert len(report.errors) == 0
    assert not report.has_code("CHAT_SEND_DEPRECATED_DETECTED")
    assert not report.has_code("TICK_LOOP_REGISTRATION_DETECTED")
    assert not report.has_code("MISSING_STARTUP_LIFECYCLE")


def test_registry_lifecycle_enforcement() -> None:
    """Verify registry rejects registration outside of the startup lifecycle phase."""
    registry = BedrockCommandRegistry()
    assert registry.phase == LifecyclePhase.PRE_STARTUP

    cmd_def = CustomCommandDefinition(
        name="admin:inspect",
        description="Inspect player inventory.",
        permission_level=CommandPermissionLevel.GAME_DIRECTORS,
    )

    with pytest.raises(RuntimeError, match="before startup event begins"):
        registry.register_command(cmd_def)

    registry.start_lifecycle()
    assert registry.phase == LifecyclePhase.STARTUP
    registry.register_command(cmd_def)
    assert "admin:inspect" in registry.registered_commands()

    registry.complete_startup()
    assert registry.phase == LifecyclePhase.RUNNING

    with pytest.raises(RuntimeError, match="after startup lifecycle ended"):
        registry.register_command(cmd_def)

    with pytest.raises(RuntimeError, match="outside of STARTUP lifecycle phase"):
        registry.register_enum("NewEnum", ["one", "two"])


def test_command_execution_and_authorization() -> None:
    """Validate permission enforcement when executing registered custom commands."""
    registry = BedrockCommandRegistry()
    registry.start_lifecycle()

    def inspect_handler(origin: CustomCommandOrigin, target: str) -> CustomCommandResult:
        return CustomCommandResult(
            status=CustomCommandStatus.SUCCESS,
            message=f"Audited {target} by {origin.source_name}",
        )

    cmd_def = CustomCommandDefinition(
        name="admin:inspect",
        description="Administrative inspect.",
        permission_level=CommandPermissionLevel.GAME_DIRECTORS,
    )
    registry.register_command(cmd_def, inspect_handler)

    unprivileged_origin = CustomCommandOrigin(
        source_name="RegularPlayer",
        permission_level=CommandPermissionLevel.ANY,
    )
    failed_result = registry.execute_command("admin:inspect", unprivileged_origin, "Steve")
    assert failed_result.status == CustomCommandStatus.FAILURE
    assert "Permission denied" in (failed_result.message or "")

    privileged_origin = CustomCommandOrigin(
        source_name="AdminOperator",
        permission_level=CommandPermissionLevel.GAME_DIRECTORS,
    )
    success_result = registry.execute_command("admin:inspect", privileged_origin, "Steve")
    assert success_result.status == CustomCommandStatus.SUCCESS
    assert success_result.message == "Audited Steve by AdminOperator"

    unknown_result = registry.execute_command("admin:unknown", privileged_origin)
    assert unknown_result.status == CustomCommandStatus.FAILURE
    assert "Unknown custom command" in (unknown_result.message or "")


def test_migration_pipeline_conversion() -> None:
    """Ensure migration pipeline converts legacy chat interception to valid TypeScript."""
    pipeline = CommandMigrationPipeline()
    legacy_code = (
        "world.beforeEvents.chatSend.subscribe((event) => {\n"
        "  if (event.message.startsWith('/inspect')) {\n"
        "    event.cancel = true;\n"
        "  }\n"
        "});\n"
    )

    commands = pipeline.extract_legacy_commands(legacy_code)
    assert commands == ["inspect"]

    generated_ts = pipeline.migrate_script_content(legacy_code)
    assert "system.beforeEvents.startup.subscribe" in generated_ts
    assert "event.customCommandRegistry" in generated_ts
    assert "registry.registerCommand" in generated_ts
    assert "CommandPermissionLevel.GameDirectors" in generated_ts
    assert "world.beforeEvents.chatSend" not in generated_ts

    ast_validator = ScriptCommandAstValidator()
    report = ast_validator.validate_script_content(generated_ts)
    assert report.is_valid
    assert len(report.errors) == 0


def test_commands_ts_exports_and_contract() -> None:
    """Verify scripts/commands.ts exports all required lifecycle and command functions."""
    script_path = Path("scripts/commands.ts")
    content = script_path.read_text(encoding="utf-8")

    expected_exports = [
        "export function executeInspectCommand",
        "export function registerAdminCommands",
        "export function registerCustomCommands",
        "export function initCommands",
    ]

    for export_signature in expected_exports:
        assert export_signature in content

    forbidden_patterns = [
        "world.beforeEvents.chatSend",
        "system.runInterval",
        "world.registerCommand",
        "system.registerCommand",
    ]

    for forbidden in forbidden_patterns:
        assert forbidden not in content
