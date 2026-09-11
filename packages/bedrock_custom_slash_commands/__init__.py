"""Bedrock Custom Slash Commands package.

Provides typed models, static AST analyzers, startup lifecycle registry,
and automated migration routines for Bedrock 1.21.70 custom command systems.
"""

from .migration import CommandMigrationPipeline
from .models import (
    CommandPermissionLevel,
    CustomCommandDefinition,
    CustomCommandOrigin,
    CustomCommandParameter,
    CustomCommandParamType,
    CustomCommandResult,
    CustomCommandStatus,
    ValidationIssue,
    ValidationReport,
)
from .registry import BedrockCommandRegistry, LifecyclePhase
from .validator import CommandDefinitionValidator, ScriptCommandAstValidator

__all__ = [
    "BedrockCommandRegistry",
    "CommandDefinitionValidator",
    "CommandMigrationPipeline",
    "CommandPermissionLevel",
    "CustomCommandDefinition",
    "CustomCommandOrigin",
    "CustomCommandParameter",
    "CustomCommandParamType",
    "CustomCommandResult",
    "CustomCommandStatus",
    "LifecyclePhase",
    "ScriptCommandAstValidator",
    "ValidationIssue",
    "ValidationReport",
]
