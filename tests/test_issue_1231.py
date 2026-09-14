"""Comprehensive test suite for Bedrock Custom Slash Command implementation (Issue #1231)."""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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


def test_models_serialization_and_deserialization() -> None:
    """Verify custom command models serialize and deserialize without loss."""
    param = CustomCommandParameter(
        name="target",
        param_type=CustomCommandParamType.STRING,
        optional=False,
    )
    serialized_param = param.to_dict()
    assert serialized_param["name"] == "target"
    assert serialized_param["type"] == "String"
    assert not serialized_param["optional"]

    restored_param = CustomCommandParameter.from_dict(serialized_param)
    assert restored_param.name == param.name
    assert restored_param.param_type == param.param_type
    assert restored_param.optional == param.optional

    definition = CustomCommandDefinition(
        name="engine:inspect",
        description="Inspect administrative engine status",
        permission_level=CommandPermissionLevel.ADMIN,
        cheats_required=True,
        mandatory_parameters=[param],
    )
    serialized_def = definition.to_dict()
    assert serialized_def["name"] == "engine:inspect"
    assert serialized_def["permissionLevel"] == 2
    assert serialized_def["cheatsRequired"] is True
    assert len(serialized_def["mandatoryParameters"]) == 1

    restored_def = CustomCommandDefinition.from_dict(serialized_def)
    assert restored_def.name == definition.name
    assert restored_def.namespace == "engine"
    assert restored_def.command_name == "inspect"
    assert restored_def.permission_level == CommandPermissionLevel.ADMIN
    assert restored_def.cheats_required is True
    assert len(restored_def.mandatory_parameters) == 1


def test_command_definition_validator_namespaces_and_format() -> None:
    """Verify command definition validation enforces namespacing and identifier rules."""
    validator = CommandDefinitionValidator()

    valid_cmd = CustomCommandDefinition(
        name="engine:inspect",
        description="Inspects engine state",
        permission_level=CommandPermissionLevel.ADMIN,
    )
    report = validator.validate_definition(valid_cmd)
    assert report.is_valid is True
    assert len(report.errors) == 0

    slash_cmd = CustomCommandDefinition(
        name="/engine:inspect",
        description="Inspects engine state",
        permission_level=CommandPermissionLevel.ADMIN,
    )
    slash_report = validator.validate_definition(slash_cmd)
    assert slash_report.is_valid is False
    assert slash_report.has_code("LEADING_SLASH_DETECTED")

    bare_cmd = CustomCommandDefinition(
        name="inspect",
        description="Inspects engine state",
        permission_level=CommandPermissionLevel.ADMIN,
    )
    bare_report = validator.validate_definition(bare_cmd)
    assert bare_report.is_valid is False
    assert bare_report.has_code("MISSING_COMMAND_NAMESPACE")


def test_command_definition_validator_permission_security() -> None:
    """Ensure administrative commands cannot be registered with ANY permission tier."""
    validator = CommandDefinitionValidator()

    insecure_admin = CustomCommandDefinition(
        name="engine:inspect",
        description="Inspects engine state",
        permission_level=CommandPermissionLevel.ANY,
    )
    report = validator.validate_definition(insecure_admin)
    assert report.is_valid is False
    assert report.has_code("INSECURE_ADMIN_PERMISSION")

    secure_admin = CustomCommandDefinition(
        name="engine:inspect",
        description="Inspects engine state",
        permission_level=CommandPermissionLevel.ADMIN,
    )
    secure_report = validator.validate_definition(secure_admin)
    assert secure_report.is_valid is True


def test_command_definition_validator_parameter_rules() -> None:
    """Verify validation detects duplicate parameters and missing enum identifiers."""
    validator = CommandDefinitionValidator()

    dup_param1 = CustomCommandParameter("target", CustomCommandParamType.STRING)
    dup_param2 = CustomCommandParameter("target", CustomCommandParamType.INTEGER)
    dup_cmd = CustomCommandDefinition(
        name="test:cmd",
        description="Test command with duplicate args",
        permission_level=CommandPermissionLevel.ADMIN,
        mandatory_parameters=[dup_param1, dup_param2],
    )
    dup_report = validator.validate_definition(dup_cmd)
    assert dup_report.is_valid is False
    assert dup_report.has_code("DUPLICATE_PARAMETER_NAME")

    missing_enum_param = CustomCommandParameter("mode", CustomCommandParamType.ENUM, enum_name=None)
    enum_cmd = CustomCommandDefinition(
        name="test:enum",
        description="Test command with enum arg",
        permission_level=CommandPermissionLevel.ADMIN,
        mandatory_parameters=[missing_enum_param],
    )
    enum_report = validator.validate_definition(enum_cmd)
    assert enum_report.is_valid is False
    assert enum_report.has_code("MISSING_ENUM_NAME")


def test_ast_validator_detects_deprecated_chat_send() -> None:
    """Verify AST validator flags legacy chatSend event interception."""
    validator = ScriptCommandAstValidator()
    legacy_code = """
    world.beforeEvents.chatSend.subscribe((event) => {
        if (event.message.startsWith('/inspect')) {
            event.cancel = true;
        }
    });
    """
    report = validator.validate_script_content(legacy_code)
    assert report.is_valid is False
    assert report.has_code("CHAT_SEND_DEPRECATED_DETECTED")


def test_ast_validator_detects_static_registry_call() -> None:
    """Verify AST validator detects invalid static invocation on CustomCommandRegistry."""
    validator = ScriptCommandAstValidator()
    broken_code = """
    system.beforeEvents.startup.subscribe(() => {
        CustomCommandRegistry.registerCommand({ name: 'engine:inspect' });
    });
    """
    report = validator.validate_script_content(broken_code)
    assert report.is_valid is False
    assert report.has_code("STATIC_REGISTRY_CALL_DETECTED")


def test_ast_validator_detects_tick_loop_registration() -> None:
    """Verify AST validator flags attempts to register commands in game loops."""
    validator = ScriptCommandAstValidator()
    tick_loop_code = """
    system.runInterval(() => {
        registry.registerCommand({ name: 'engine:inspect' });
    });
    """
    report = validator.validate_script_content(tick_loop_code)
    assert report.is_valid is False
    assert report.has_code("TICK_LOOP_REGISTRATION_DETECTED")


def test_ast_validator_validates_commands_ts_source() -> None:
    """Verify the repository commands.ts script passes AST validation cleanly."""
    validator = ScriptCommandAstValidator()
    commands_path = Path(__file__).resolve().parent.parent / "scripts" / "commands.ts"
    assert commands_path.is_file()

    report = validator.validate_script_file(str(commands_path))
    assert report.is_valid is True
    assert len(report.errors) == 0


def test_registry_lifecycle_phases_and_state_guards() -> None:
    """Verify registry strictly enforces PRE_STARTUP, STARTUP, and RUNNING phase guards."""
    registry = BedrockCommandRegistry()
    assert registry.phase == LifecyclePhase.PRE_STARTUP

    cmd_def = CustomCommandDefinition(
        name="engine:inspect",
        description="Inspect administrative state",
        permission_level=CommandPermissionLevel.ADMIN,
    )

    with pytest.raises(RuntimeError, match="before startup event begins"):
        registry.register_command(cmd_def)

    registry.start_lifecycle()
    assert registry.phase == LifecyclePhase.STARTUP
    registry.register_command(cmd_def)
    assert "engine:inspect" in registry.registered_commands()

    registry.complete_startup()
    assert registry.phase == LifecyclePhase.RUNNING

    late_def = CustomCommandDefinition(
        name="engine:late",
        description="Late registered command",
        permission_level=CommandPermissionLevel.ADMIN,
    )
    with pytest.raises(RuntimeError, match="after startup lifecycle ended"):
        registry.register_command(late_def)


def test_registry_execution_and_permission_authorization() -> None:
    """Verify command execution enforces permission gating across caller tiers."""
    registry = BedrockCommandRegistry()
    registry.start_lifecycle()

    def inspect_handler(origin: CustomCommandOrigin) -> CustomCommandResult:
        return CustomCommandResult(
            status=CustomCommandStatus.SUCCESS,
            message=f"Inspected by {origin.source_name}",
        )

    cmd_def = CustomCommandDefinition(
        name="engine:inspect",
        description="Inspect administrative state",
        permission_level=CommandPermissionLevel.ADMIN,
    )
    registry.register_command(cmd_def, callback=inspect_handler)

    unauthorized_caller = CustomCommandOrigin(
        source_name="PlayerA",
        permission_level=CommandPermissionLevel.ANY,
    )
    denied_result = registry.execute_command("engine:inspect", unauthorized_caller)
    assert denied_result.status == CustomCommandStatus.FAILURE
    assert "Permission denied" in (denied_result.message or "")

    authorized_admin = CustomCommandOrigin(
        source_name="AdminSteve",
        permission_level=CommandPermissionLevel.ADMIN,
    )
    granted_result = registry.execute_command("engine:inspect", authorized_admin)
    assert granted_result.status == CustomCommandStatus.SUCCESS
    assert "Inspected by AdminSteve" in (granted_result.message or "")


def test_command_migration_pipeline() -> None:
    """Verify migration pipeline transforms legacy chat patterns into valid startup hooks."""
    pipeline = CommandMigrationPipeline()
    legacy_snippet = """
    world.beforeEvents.chatSend.subscribe((event) => {
        if (event.message.startsWith('/inspect')) {
            executeLegacyInspect(event.sender);
        }
    });
    """
    commands = pipeline.extract_legacy_commands(legacy_snippet)
    assert "inspect" in commands

    modern_ts = pipeline.migrate_script_content(legacy_snippet)
    assert "system.beforeEvents.startup.subscribe" in modern_ts
    assert "event.customCommandRegistry" in modern_ts
    assert "registry.registerCommand" in modern_ts
    assert "admin:inspect" in modern_ts

    ast_validator = ScriptCommandAstValidator()
    report = ast_validator.validate_script_content(modern_ts)
    assert report.is_valid is True
