#!/usr/bin/env python3
"""Standalone verifier for Bedrock Custom Slash Commands (#1323).

Validates model configurations, AST static analysis, startup lifecycle rules,
permission gating enforcement, and automated migration logic.
"""

from pathlib import Path
import sys

try:
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
except ModuleNotFoundError:
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
        CustomCommandStatus,
        InspectCommandService,
        LifecyclePhase,
        ScriptCommandAstValidator,
    )


def verify_models() -> bool:
    """Verify data model serialization and identity properties."""
    filter_param = CustomCommandParameter(
        name="filter_mode",
        param_type=CustomCommandParamType.ENUM,
        enum_name="InspectionFilter",
        optional=True,
    )
    admin_definition = CustomCommandDefinition(
        name="server:inspect",
        description="Inspect administrative server status and diagnostics.",
        permission_level=CommandPermissionLevel.ADMIN,
        cheats_required=True,
        mandatory_parameters=[],
        optional_parameters=[filter_param],
    )

    serialized = admin_definition.to_dict()
    unpacked = CustomCommandDefinition.from_dict(serialized)

    has_ns = admin_definition.has_namespace and admin_definition.namespace == "server"
    correct_name = admin_definition.command_name == "inspect"
    matches = (
        unpacked.name == "server:inspect"
        and len(unpacked.optional_parameters) == 1
        and unpacked.permission_level == CommandPermissionLevel.ADMIN
    )

    return has_ns and correct_name and matches


def verify_static_ast_validation() -> bool:
    """Validate static analysis detects bugs and passes on corrected scripts."""
    validator = ScriptCommandAstValidator()
    buggy_snippet = (
        "import { CustomCommandRegistry } from '@minecraft/server';\n"
        "export function registerInspectCommand() {\n"
        "  CustomCommandRegistry.registerCommand('inspect', () => {});\n"
        "}\n"
    )
    buggy_report = validator.validate_script_content(buggy_snippet)
    if buggy_report.is_valid or not buggy_report.has_code(
        "STATIC_REGISTRY_INVOCATION_DETECTED"
    ):
        return False

    target_path = Path("scripts/commands/inspect.ts")
    if not target_path.is_file():
        return False

    valid_report = validator.validate_script_file(str(target_path))
    return valid_report.is_valid


def verify_command_definition_validation() -> bool:
    """Validate command definition schema constraints and permission checks."""
    validator = CommandDefinitionValidator()

    valid_def = CustomCommandDefinition(
        name="engine:inspect",
        description="Inspect engine state.",
        permission_level=CommandPermissionLevel.ADMIN,
    )
    valid_report = validator.validate_definition(valid_def)
    if not valid_report.is_valid:
        return False

    invalid_slash = CustomCommandDefinition(
        name="/inspect",
        description="Leading slash invalid.",
        permission_level=CommandPermissionLevel.ADMIN,
    )
    invalid_report = validator.validate_definition(invalid_slash)
    if invalid_report.is_valid or not invalid_report.has_code(
        "LEADING_SLASH_DETECTED"
    ):
        return False

    return True


def verify_registry_lifecycle_and_permissions() -> bool:
    """Verify registry lifecycle transitions and authorization checks."""
    registry = BedrockCommandRegistry()
    if registry.phase != LifecyclePhase.PRE_STARTUP:
        return False

    registry.start_lifecycle()
    InspectCommandService.register_inspect_command(registry)
    registry.complete_startup()

    guest_origin = CustomCommandOrigin(
        source_type="player",
        source_name="Guest",
        permission_level=CommandPermissionLevel.NORMAL,
    )
    blocked_result = registry.execute_command("inspect", guest_origin)

    admin_origin = CustomCommandOrigin(
        source_type="player",
        source_name="Administrator",
        source_entity_id="admin-uuid",
        location=(0.0, 64.0, 0.0),
        permission_level=CommandPermissionLevel.ADMIN,
    )
    allowed_result = registry.execute_command("inspect", admin_origin)

    return (
        blocked_result.status == CustomCommandStatus.FAILURE
        and allowed_result.status == CustomCommandStatus.SUCCESS
    )


def verify_inspect_service_telemetry() -> bool:
    """Verify inspection service generates telemetry reports across contexts."""
    entity_origin = CustomCommandOrigin(
        source_type="entity",
        source_name="TargetEntity",
        source_entity_id="entity-id-1",
        location=(5.0, 72.0, -10.0),
        permission_level=CommandPermissionLevel.ADMIN,
    )
    entity_result = InspectCommandService.execute_inspect(entity_origin)

    block_origin = CustomCommandOrigin(
        source_type="block",
        location=(10.0, 20.0, 30.0),
        permission_level=CommandPermissionLevel.ADMIN,
    )
    block_result = InspectCommandService.execute_inspect(block_origin)

    console_origin = CustomCommandOrigin(
        source_type="server",
        permission_level=CommandPermissionLevel.ADMIN,
    )
    console_result = InspectCommandService.execute_inspect(console_origin)

    return (
        entity_result.status == CustomCommandStatus.SUCCESS
        and block_result.status == CustomCommandStatus.SUCCESS
        and console_result.status == CustomCommandStatus.SUCCESS
    )


def verify_migration_pipeline() -> bool:
    """Verify conversion of legacy/broken syntax to modern Bedrock API."""
    pipeline = CommandMigrationPipeline()
    buggy_snippet = (
        "function init() {\n"
        "  CustomCommandRegistry.registerCommand('inspect', () => {});\n"
        "}\n"
    )

    migrated_code = pipeline.migrate_script_content(buggy_snippet)
    has_event_registry = "event.customCommandRegistry.registerCommand" in migrated_code
    no_static_call = "CustomCommandRegistry.registerCommand" not in migrated_code

    return has_event_registry and no_static_call


def verify_disk_artifacts() -> bool:
    """Verify physical TypeScript and JavaScript file presence and contents."""
    required_files = [
        Path("scripts/commands/types.ts"),
        Path("scripts/commands/inspect.ts"),
        Path("scripts/commands/index.ts"),
        Path("scripts/startup.ts"),
        Path("scripts/main.ts"),
    ]

    for file_path in required_files:
        if not file_path.is_file():
            return False

    inspect_content = Path("scripts/commands/inspect.ts").read_text(
        encoding="utf-8"
    )
    expected_tokens = [
        "export function registerInspectCommand",
        "export function executeInspectCommand",
        "CommandPermissionLevel.Admin",
        "resolveRegistry",
    ]

    return all(token in inspect_content for token in expected_tokens)


def main() -> int:
    """Run all verification suites and output structured summary."""
    verifications = [
        ("Data Models & Serialization", verify_models),
        ("Script AST Static Analysis", verify_static_ast_validation),
        ("Command Definition Validation", verify_command_definition_validation),
        ("Registry Lifecycle & Authorization", verify_registry_lifecycle_and_permissions),
        ("Inspection Telemetry Generation", verify_inspect_service_telemetry),
        ("Migration Pipeline Translation", verify_migration_pipeline),
        ("Physical Disk Artifacts Integrity", verify_disk_artifacts),
    ]

    all_passed = True
    for label, check_func in verifications:
        passed = check_func()
        status_str = "PASS" if passed else "FAIL"
        print(f"[{status_str}] {label}")
        if not passed:
            all_passed = False

    if all_passed:
        print("[SUCCESS] All Issue #1323 verification checks passed.")
        return 0

    print("[FAILURE] One or more verification checks failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
