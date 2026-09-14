#!/usr/bin/env python3
"""Standalone verifier for Bedrock Custom Slash Commands (#1309).

Validates model configurations, AST static analysis, startup lifecycle rules,
command execution permissions, and automated migration logic.
"""

from pathlib import Path
import sys

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


def verify_models() -> bool:
    """Verify data model serialization and identity properties."""
    param = CustomCommandParameter(
        name="target",
        param_type=CustomCommandParamType.STRING,
    )
    definition = CustomCommandDefinition(
        name="engine:inspect",
        description="Inspect administrative engine status and entity metrics.",
        permission_level=CommandPermissionLevel.ADMIN,
        mandatory_parameters=[param],
    )

    data = definition.to_dict()
    restored = CustomCommandDefinition.from_dict(data)

    valid_namespace = definition.has_namespace and definition.namespace == "engine"
    valid_name = definition.command_name == "inspect"
    valid_roundtrip = (
        restored.name == definition.name
        and len(restored.mandatory_parameters) == 1
        and restored.permission_level == CommandPermissionLevel.ADMIN
    )

    return valid_namespace and valid_name and valid_roundtrip


def verify_command_definition_validation() -> bool:
    """Validate definition schema constraints and permission checks."""
    validator = CommandDefinitionValidator()

    valid_def = CustomCommandDefinition(
        name="engine:inspect",
        description="Inspect administrative engine status.",
        permission_level=CommandPermissionLevel.ADMIN,
    )
    valid_report = validator.validate_definition(valid_def)
    if not valid_report.is_valid:
        return False

    invalid_def = CustomCommandDefinition(
        name="/engine:inspect",
        description="Leading slash invalid.",
        permission_level=CommandPermissionLevel.ADMIN,
    )
    invalid_report = validator.validate_definition(invalid_def)
    if invalid_report.is_valid or not invalid_report.has_code("LEADING_SLASH_DETECTED"):
        return False

    insecure_def = CustomCommandDefinition(
        name="engine:inspect",
        description="Insecure permission level.",
        permission_level=CommandPermissionLevel.ANY,
    )
    insecure_report = validator.validate_definition(insecure_def)
    if insecure_report.is_valid or not insecure_report.has_code("INSECURE_ADMIN_PERMISSION"):
        return False

    return True


def verify_script_ast_validation() -> bool:
    """Validate scripts/commands.ts passes all Bedrock static analysis rules."""
    validator = ScriptCommandAstValidator()
    target_path = Path("scripts/commands.ts")
    if not target_path.is_file():
        return False

    report = validator.validate_script_file(str(target_path))
    if not report.is_valid:
        return False

    has_deprecated = report.has_code("CHAT_SEND_DEPRECATED_DETECTED")
    has_tick_loop = report.has_code("TICK_LOOP_REGISTRATION_DETECTED")
    return not has_deprecated and not has_tick_loop


def verify_registry_lifecycle() -> bool:
    """Verify registry lifecycle transitions and authorization checks."""
    registry = BedrockCommandRegistry()
    if registry.phase != LifecyclePhase.PRE_STARTUP:
        return False

    def handler(origin: CustomCommandOrigin, target: str) -> CustomCommandResult:
        return CustomCommandResult(
            status=CustomCommandStatus.SUCCESS,
            message=f"{target}:{origin.source_name}",
        )

    cmd_def = CustomCommandDefinition(
        name="engine:inspect",
        description="Inspect engine state.",
        permission_level=CommandPermissionLevel.ADMIN,
    )

    registry.start_lifecycle()
    registry.register_command(cmd_def, handler)
    registry.complete_startup()

    operator_origin = CustomCommandOrigin(
        source_name="AdminOperator",
        permission_level=CommandPermissionLevel.ADMIN,
    )
    result = registry.execute_command("engine:inspect", operator_origin, "Alex")

    user_origin = CustomCommandOrigin(
        source_name="GuestUser",
        permission_level=CommandPermissionLevel.ANY,
    )
    blocked_result = registry.execute_command("engine:inspect", user_origin, "Alex")

    return (
        result.status == CustomCommandStatus.SUCCESS
        and blocked_result.status == CustomCommandStatus.FAILURE
    )


def verify_migration_pipeline() -> bool:
    """Verify conversion of legacy chatSend interception to modern TypeScript."""
    pipeline = CommandMigrationPipeline()
    legacy_snippet = (
        "world.beforeEvents.chatSend.subscribe((evt) => {\n"
        "  const text = evt.message;\n"
        "  if (text.startsWith('/inspect') || text.startsWith('/freeze')) {\n"
        "    evt.cancel = true;\n"
        "  }\n"
        "});\n"
    )

    migrated_code = pipeline.migrate_script_content(legacy_snippet)
    validator = ScriptCommandAstValidator()
    report = validator.validate_script_content(migrated_code)

    has_startup = "system.beforeEvents.startup.subscribe" in migrated_code
    no_chat_send = "world.beforeEvents.chatSend" not in migrated_code

    return report.is_valid and has_startup and no_chat_send


def verify_disk_artifacts() -> bool:
    """Verify physical TypeScript file presence and structural signatures."""
    files_to_check = [
        Path("manifest.json"),
        Path("package.json"),
        Path("tsconfig.json"),
        Path("scripts/commands/types.ts"),
        Path("scripts/commands/inspect.ts"),
        Path("scripts/startup.ts"),
        Path("scripts/commands.ts"),
    ]

    for file_path in files_to_check:
        if not file_path.is_file():
            return False

    inspect_content = Path("scripts/commands/inspect.ts").read_text(encoding="utf-8")
    required_signatures = [
        "export function buildInspectionReport",
        "export function validateCommandPermission",
        "export function executeInspectCommand",
        "export function registerInspectCommand",
        "CommandPermissionLevel.Admin",
    ]

    return all(sig in inspect_content for sig in required_signatures)


def main() -> int:
    """Run all verification suites and output structured summary."""
    verifications = [
        ("Data Models & Serialization", verify_models),
        ("Command Definition Validation", verify_command_definition_validation),
        ("Script AST Static Analysis", verify_script_ast_validation),
        ("Registry Lifecycle & Authorization", verify_registry_lifecycle),
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
        print("[SUCCESS] All Issue #1309 verification checks passed.")
        return 0

    print("[FAILURE] One or more verification checks failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
