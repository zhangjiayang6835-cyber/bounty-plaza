"""Runtime simulation of Bedrock CustomCommandRegistry lifecycle and execution."""

from collections.abc import Callable
from enum import Enum
from typing import Any, Optional, Union

from .models import (
    CommandPermissionLevel,
    CustomCommandDefinition,
    CustomCommandOrigin,
    CustomCommandResult,
    CustomCommandStatus,
)
from .validator import CommandDefinitionValidator


class LifecyclePhase(str, Enum):
    """Execution phases in the Bedrock scripting engine."""

    PRE_STARTUP = "PRE_STARTUP"
    STARTUP = "STARTUP"
    RUNNING = "RUNNING"


class BedrockCommandRegistry:
    """Manages custom command registration and enforces startup lifecycle constraints."""

    def __init__(self) -> None:
        """Initialize an empty command registry in PRE_STARTUP state."""
        self._commands: dict[
            str, tuple[CustomCommandDefinition, Optional[Callable[..., Any]]]
        ] = {}
        self._enums: dict[str, list[str]] = {}
        self._phase: LifecyclePhase = LifecyclePhase.PRE_STARTUP
        self._validator = CommandDefinitionValidator()

    @property
    def phase(self) -> LifecyclePhase:
        """Return current scripting engine lifecycle phase."""
        return self._phase

    def start_lifecycle(self) -> None:
        """Advance lifecycle to STARTUP phase allowing command registration."""
        self._phase = LifecyclePhase.STARTUP

    def complete_startup(self) -> None:
        """Advance lifecycle to RUNNING phase locking command registration."""
        self._phase = LifecyclePhase.RUNNING

    def register_enum(self, enum_name: str, values: list[str]) -> None:
        """Register a named enumeration for custom command arguments."""
        if self._phase != LifecyclePhase.STARTUP:
            raise RuntimeError(
                f"Cannot register enum '{enum_name}' outside of STARTUP lifecycle phase."
            )
        if not enum_name or not values:
            raise ValueError("Enum name and values list must be non-empty.")
        self._enums[enum_name] = list(values)

    def register_command(
        self,
        command: Union[CustomCommandDefinition, str],
        callback_or_options: Optional[Union[Callable[..., Any], dict[str, Any]]] = None,
        maybe_callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        """Register a custom command definition and handler during STARTUP phase."""
        if self._phase == LifecyclePhase.PRE_STARTUP:
            name = command if isinstance(command, str) else command.name
            raise RuntimeError(
                f"Cannot register command '{name}' before startup event begins."
            )
        if self._phase == LifecyclePhase.RUNNING:
            name = command if isinstance(command, str) else command.name
            raise RuntimeError(
                f"Cannot register custom command '{name}' after startup lifecycle ended."
            )

        if isinstance(command, str):
            options = callback_or_options if isinstance(callback_or_options, dict) else {}
            callback = maybe_callback or (
                callback_or_options if callable(callback_or_options) else None
            )
            perm = options.get("permissionLevel", CommandPermissionLevel.ANY)
            if not isinstance(perm, CommandPermissionLevel):
                perm = CommandPermissionLevel(perm)
            definition = CustomCommandDefinition(
                name=command,
                description=options.get("description", ""),
                permission_level=perm,
                cheats_required=options.get("cheatsRequired", False),
            )
        else:
            definition = command
            callback = callback_or_options if callable(callback_or_options) else None

        report = self._validator.validate_definition(definition)
        if not report.is_valid:
            errors = [issue.message for issue in report.errors]
            raise ValueError(f"Invalid command configuration: {errors}")

        self._commands[definition.name] = (definition, callback)

    def get_command(self, identifier: str) -> Optional[CustomCommandDefinition]:
        """Look up a registered command definition by identifier."""
        entry = self._commands.get(identifier)
        if entry is None:
            return None
        return entry[0]

    def registered_commands(self) -> list[str]:
        """Return sorted list of all registered command identifiers."""
        return sorted(self._commands.keys())

    def execute_command(
        self,
        identifier: str,
        origin: CustomCommandOrigin,
        *args: Any,
    ) -> CustomCommandResult:
        """Execute a registered command callback verifying caller permission level."""
        entry = self._commands.get(identifier)
        if entry is None:
            return CustomCommandResult(
                status=CustomCommandStatus.FAILURE,
                message=f"Unknown custom command: {identifier}",
            )

        definition, callback = entry

        if origin.permission_level < definition.permission_level:
            return CustomCommandResult(
                status=CustomCommandStatus.FAILURE,
                message=(
                    f"Permission denied: Command '{identifier}' requires permission level "
                    f"{definition.permission_level.name} ({definition.permission_level.value}), "
                    f"caller has {origin.permission_level.name} ({origin.permission_level.value})."
                ),
            )

        if callback is None:
            return CustomCommandResult(
                status=CustomCommandStatus.SUCCESS,
                message=f"Command '{identifier}' executed with no handler callback.",
            )

        raw_result = callback(origin, *args)
        if isinstance(raw_result, CustomCommandResult):
            return raw_result

        return CustomCommandResult(
            status=CustomCommandStatus.SUCCESS,
            message=f"Command '{identifier}' executed successfully.",
        )
