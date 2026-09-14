"""Validators for Bedrock custom slash command definitions and TypeScript scripts."""

from pathlib import Path
import re
from typing import Optional

from .models import (
    CommandPermissionLevel,
    CustomCommandDefinition,
    CustomCommandParamType,
    ValidationReport,
)

ADMIN_COMMAND_KEYWORDS = ("inspect", "ban", "kick", "mute", "freeze", "teleport_admin")


class CommandDefinitionValidator:
    """Validates structural correctness of Bedrock custom command configurations."""

    def validate_batch(
        self,
        definitions: list[CustomCommandDefinition],
    ) -> list[ValidationReport]:
        """Validate a collection of custom command definitions."""
        return [self.validate_definition(defn) for defn in definitions]

    def validate_definition(self, definition: CustomCommandDefinition) -> ValidationReport:
        """Evaluate a custom command configuration against Bedrock engine standards."""
        report = ValidationReport()

        if not definition.name or not definition.name.strip():
            report.add_issue(
                "ERROR",
                "EMPTY_COMMAND_NAME",
                "Command name cannot be empty.",
            )
            return report

        if definition.name.startswith("/"):
            report.add_issue(
                "ERROR",
                "LEADING_SLASH_DETECTED",
                "Custom command names must not contain leading slash in registry.",
            )

        if not definition.has_namespace:
            report.add_issue(
                "ERROR",
                "MISSING_COMMAND_NAMESPACE",
                (
                    f"Command '{definition.name}' must specify a namespace prefix "
                    "(e.g. 'admin:inspect')."
                ),
            )
        else:
            namespace, cmd_name = definition.name.split(":", 1)
            if not namespace or not cmd_name:
                report.add_issue(
                    "ERROR",
                    "MALFORMED_COMMAND_IDENTIFIER",
                    f"Command identifier '{definition.name}' has empty namespace or name segment.",
                )

        if not definition.description or not definition.description.strip():
            report.add_issue(
                "ERROR",
                "EMPTY_COMMAND_DESCRIPTION",
                f"Command '{definition.name}' must have a descriptive help text.",
            )

        self._validate_permission_security(definition, report)
        self._validate_parameters(definition, report)

        return report

    def _validate_permission_security(
        self,
        definition: CustomCommandDefinition,
        report: ValidationReport,
    ) -> None:
        """Ensure administrative commands enforce elevated permission levels."""
        lower_name = definition.name.lower()
        is_admin_cmd = any(keyword in lower_name for keyword in ADMIN_COMMAND_KEYWORDS)

        if is_admin_cmd and definition.permission_level == CommandPermissionLevel.ANY:
            report.add_issue(
                "ERROR",
                "INSECURE_ADMIN_PERMISSION",
                f"Administrative command '{definition.name}' must not use permission level ANY.",
            )

    def _validate_parameters(
        self,
        definition: CustomCommandDefinition,
        report: ValidationReport,
    ) -> None:
        """Verify parameter uniqueness and enum constraints."""
        seen_names: set[str] = set()

        for param in definition.mandatory_parameters + definition.optional_parameters:
            if param.name in seen_names:
                report.add_issue(
                    "ERROR",
                    "DUPLICATE_PARAMETER_NAME",
                    f"Duplicate parameter name '{param.name}' in command '{definition.name}'.",
                )
            seen_names.add(param.name)

            if param.param_type == CustomCommandParamType.ENUM and not param.enum_name:
                report.add_issue(
                    "ERROR",
                    "MISSING_ENUM_NAME",
                    f"Parameter '{param.name}' requires enum_name when param_type is ENUM.",
                )


class ScriptCommandAstValidator:
    """Performs static analysis on Bedrock TypeScript/JavaScript script files."""

    def validate_script_content(
        self,
        content: str,
        source_path: Optional[str] = None,
    ) -> ValidationReport:
        """Scan script source for deprecated patterns and verify startup lifecycle."""
        report = ValidationReport()
        lines = content.splitlines()

        self._check_deprecated_chat_send(lines, report)
        self._check_tick_loop_registration(lines, report)
        self._check_undefined_engine_calls(lines, report)
        self._check_startup_lifecycle(content, report)
        self._check_permission_enums(content, report)

        if source_path and not Path(source_path).is_file():
            report.add_issue(
                "WARNING",
                "SOURCE_FILE_NOT_FOUND",
                f"Referenced source file does not exist on disk: {source_path}",
            )

        return report

    def validate_script_file(self, file_path: str) -> ValidationReport:
        """Read and validate script file from the local filesystem."""
        path = Path(file_path)
        if not path.is_file():
            report = ValidationReport(is_valid=False)
            report.add_issue(
                "ERROR",
                "FILE_NOT_FOUND",
                f"Target script file does not exist: {file_path}",
            )
            return report

        content = path.read_text(encoding="utf-8")
        return self.validate_script_content(content, source_path=str(path))

    def _check_deprecated_chat_send(
        self,
        lines: list[str],
        report: ValidationReport,
    ) -> None:
        """Flag usage of deprecated chatSend interception events."""
        pattern = re.compile(r"world\.beforeEvents\.chatSend")
        for idx, line in enumerate(lines, start=1):
            if pattern.search(line):
                report.add_issue(
                    "ERROR",
                    "CHAT_SEND_DEPRECATED_DETECTED",
                    "Deprecated chatSend interception detected. Use customCommandRegistry.",
                    line_number=idx,
                )

    def _check_tick_loop_registration(
        self,
        lines: list[str],
        report: ValidationReport,
    ) -> None:
        """Detect invalid registration attempts inside runtime game tick loops."""
        interval_pattern = re.compile(r"system\.(runInterval|runTimeout|run)\s*\(")
        for idx, line in enumerate(lines, start=1):
            if interval_pattern.search(line):
                report.add_issue(
                    "ERROR",
                    "TICK_LOOP_REGISTRATION_DETECTED",
                    "Commands must not be registered inside tick loops (runInterval/run).",
                    line_number=idx,
                )

    def _check_undefined_engine_calls(
        self,
        lines: list[str],
        report: ValidationReport,
    ) -> None:
        """Flag invalid calls like world.registerCommand or system.registerCommand."""
        invalid_pattern = re.compile(r"(world|system)\.registerCommand\s*\(")
        for idx, line in enumerate(lines, start=1):
            if invalid_pattern.search(line):
                report.add_issue(
                    "ERROR",
                    "UNDEFINED_REGISTRY_ACCESS",
                    "Cannot call registerCommand directly on world or system object.",
                    line_number=idx,
                )

    def _check_startup_lifecycle(
        self,
        content: str,
        report: ValidationReport,
    ) -> None:
        """Verify presence of startup lifecycle event subscription and registry access."""
        startup_pattern = re.compile(r"system\.beforeEvents\.startup\.subscribe")
        registry_ref_pattern = re.compile(r"customCommandRegistry")
        register_call_pattern = re.compile(r"\.registerCommand\s*\(")

        if not startup_pattern.search(content):
            report.add_issue(
                "ERROR",
                "MISSING_STARTUP_LIFECYCLE",
                "Script must subscribe to system.beforeEvents.startup for custom commands.",
            )

        if not registry_ref_pattern.search(content):
            report.add_issue(
                "ERROR",
                "MISSING_REGISTRY_REFERENCE",
                "Script does not access customCommandRegistry from startup event.",
            )

        if not register_call_pattern.search(content):
            report.add_issue(
                "ERROR",
                "MISSING_REGISTRY_INVOCATION",
                "Script does not invoke registerCommand on registry.",
            )

    def _check_permission_enums(
        self,
        content: str,
        report: ValidationReport,
    ) -> None:
        """Verify script imports and utilizes correct CommandPermissionLevel enum."""
        if "CommandPermissionLevel" not in content:
            report.add_issue(
                "ERROR",
                "MISSING_PERMISSION_ENUM_IMPORT",
                "Script must import CommandPermissionLevel from @minecraft/server.",
            )
        elif "CommandPermissionLevel.GameDirectors" not in content:
            report.add_issue(
                "WARNING",
                "MISSING_GAME_DIRECTORS_PERMISSION",
                "Administration commands should enforce CommandPermissionLevel.GameDirectors.",
            )
