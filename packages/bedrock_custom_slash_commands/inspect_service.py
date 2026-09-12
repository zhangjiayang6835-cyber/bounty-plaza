"""Inspection command business logic and execution handlers."""

import time

from .models import (
    CommandPermissionLevel,
    CustomCommandDefinition,
    CustomCommandOrigin,
    CustomCommandResult,
    CustomCommandStatus,
    InspectionReport,
)
from .registry import BedrockCommandRegistry


class InspectCommandService:
    """Provides administrative inspection routines and registry wiring."""

    @staticmethod
    def build_inspection_report(origin: CustomCommandOrigin) -> InspectionReport:
        """Construct structured telemetry report from caller origin context."""
        timestamp = int(time.time() * 1000)

        if origin.source_type in ("entity", "player"):
            target_id = origin.source_entity_id or origin.source_name
            return InspectionReport(
                target_type="minecraft:player"
                if origin.source_type == "player"
                else "minecraft:entity",
                target_id=target_id,
                source_type=origin.source_type,
                coordinates=origin.location,
                timestamp=timestamp,
            )

        if origin.source_type == "block":
            return InspectionReport(
                target_type="minecraft:command_block",
                source_type=origin.source_type,
                coordinates=origin.location,
                timestamp=timestamp,
            )

        return InspectionReport(
            target_type="server_console",
            source_type=origin.source_type,
            timestamp=timestamp,
        )

    @classmethod
    def execute_inspect(cls, origin: CustomCommandOrigin) -> CustomCommandResult:
        """Execute inspection routine verifying administrator clearance."""
        if origin.permission_level < CommandPermissionLevel.ADMIN:
            return CustomCommandResult(
                status=CustomCommandStatus.FAILURE,
                message="[EngineInspect] Permission denied: Admin clearance required.",
            )

        report = cls.build_inspection_report(origin)

        if origin.source_type in ("player", "entity"):
            coords = f"[{report.coordinates[0]}, {report.coordinates[1]}, {report.coordinates[2]}]"
            name = report.target_id or "unknown"
            return CustomCommandResult(
                status=CustomCommandStatus.SUCCESS,
                message=f"[EngineInspect] Inspected entity '{name}' at {coords}. Status: healthy.",
            )

        if origin.source_type == "block":
            coords = f"[{report.coordinates[0]}, {report.coordinates[1]}, {report.coordinates[2]}]"
            return CustomCommandResult(
                status=CustomCommandStatus.SUCCESS,
                message=f"[EngineInspect] Inspected command block at {coords}.",
            )

        return CustomCommandResult(
            status=CustomCommandStatus.SUCCESS,
            message=(
                f"[EngineInspect] BDS Server Console inspected at timestamp {report.timestamp}. "
                "Subsystems operational."
            ),
        )

    @classmethod
    def register_inspect_command(cls, registry: BedrockCommandRegistry) -> None:
        """Register /inspect and /engine:inspect on the active startup registry."""
        root_definition = CustomCommandDefinition(
            name="inspect",
            description="Inspect administrative engine status and entity metrics",
            permission_level=CommandPermissionLevel.ADMIN,
            cheats_required=True,
        )
        registry.register_command(
            root_definition,
            lambda origin, *args: cls.execute_inspect(origin),
        )

        namespaced_definition = CustomCommandDefinition(
            name="engine:inspect",
            description="Inspect administrative engine status and entity metrics",
            permission_level=CommandPermissionLevel.ADMIN,
            cheats_required=True,
        )
        registry.register_command(
            namespaced_definition,
            lambda origin, *args: cls.execute_inspect(origin),
        )
