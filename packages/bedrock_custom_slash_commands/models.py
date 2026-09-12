"""Data models and type definitions for Minecraft Bedrock Custom Slash Commands."""

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Optional


class CommandPermissionLevel(IntEnum):
    """Execution permission levels for Bedrock commands."""

    ANY = 0
    NORMAL = 0
    GAME_DIRECTORS = 1
    OPERATOR = 1
    ADMIN = 2
    HOST = 3
    OWNER = 4


class CustomCommandParamType(str, Enum):
    """Supported parameter types for Bedrock custom commands."""

    BOOLEAN = "Boolean"
    FLOAT = "Float"
    INTEGER = "Integer"
    STRING = "String"
    ENTITY_SELECTOR = "EntitySelector"
    BLOCK_TYPE = "BlockType"
    ITEM_TYPE = "ItemType"
    ENUM = "Enum"
    LOCATION = "Location"


class CustomCommandStatus(str, Enum):
    """Result status codes returned by custom command execution."""

    SUCCESS = "Success"
    FAILURE = "Failure"


class CustomCommandSource(str, Enum):
    """Origin sources capable of triggering custom command callbacks."""

    BLOCK = "Block"
    ENTITY = "Entity"
    NPC_DIALOGUE = "NPCDialogue"
    SERVER = "Server"


@dataclass
class CustomCommandParameter:
    """Represents a parameter definition for a custom slash command."""

    name: str
    param_type: CustomCommandParamType
    enum_name: Optional[str] = None
    optional: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert parameter definition to a serializable dictionary."""
        payload: dict[str, Any] = {
            "name": self.name,
            "type": self.param_type.value,
            "optional": self.optional,
        }
        if self.enum_name is not None:
            payload["enumName"] = self.enum_name
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomCommandParameter":
        """Construct parameter definition from a dictionary."""
        param_type = CustomCommandParamType(data["type"])
        return cls(
            name=data["name"],
            param_type=param_type,
            enum_name=data.get("enumName"),
            optional=data.get("optional", False),
        )


@dataclass
class CustomCommandDefinition:
    """Represents the complete configuration of a Bedrock custom command."""

    name: str
    description: str
    permission_level: CommandPermissionLevel = CommandPermissionLevel.ANY
    cheats_required: bool = False
    mandatory_parameters: list[CustomCommandParameter] = field(default_factory=list)
    optional_parameters: list[CustomCommandParameter] = field(default_factory=list)

    @property
    def has_namespace(self) -> bool:
        """Return True if command identifier specifies a namespace."""
        return ":" in self.name

    @property
    def namespace(self) -> str:
        """Return the namespace segment of the command identifier."""
        if ":" in self.name:
            return self.name.split(":", 1)[0]
        return ""

    @property
    def command_name(self) -> str:
        """Return the base command name without namespace."""
        if ":" in self.name:
            return self.name.split(":", 1)[1]
        return self.name

    def to_dict(self) -> dict[str, Any]:
        """Convert command definition to a dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "permissionLevel": self.permission_level.value,
            "cheatsRequired": self.cheats_required,
            "mandatoryParameters": [
                param.to_dict() for param in self.mandatory_parameters
            ],
            "optionalParameters": [
                param.to_dict() for param in self.optional_parameters
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomCommandDefinition":
        """Construct command definition from a dictionary."""
        permission = CommandPermissionLevel(data.get("permissionLevel", 0))
        mandatory = [
            CustomCommandParameter.from_dict(item)
            for item in data.get("mandatoryParameters", [])
        ]
        optional = [
            CustomCommandParameter.from_dict(item)
            for item in data.get("optionalParameters", [])
        ]
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            permission_level=permission,
            cheats_required=data.get("cheatsRequired", False),
            mandatory_parameters=mandatory,
            optional_parameters=optional,
        )


@dataclass
class CustomCommandOrigin:
    """Represents the caller context invoking a custom command."""

    source_type: str = "player"
    source_name: str = "ServerAdmin"
    source_entity_id: Optional[str] = None
    dimension: str = "overworld"
    location: tuple[float, float, float] = (0.0, 0.0, 0.0)
    permission_level: CommandPermissionLevel = CommandPermissionLevel.ANY


@dataclass
class CustomCommandResult:
    """Represents the execution outcome of a custom command callback."""

    status: CustomCommandStatus = CustomCommandStatus.SUCCESS
    message: Optional[str] = None


@dataclass
class InspectionReport:
    """Represents the structured payload generated by an inspect execution."""

    target_type: str
    source_type: str
    timestamp: int
    target_id: Optional[str] = None
    coordinates: Optional[tuple[float, float, float]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert inspection report to dictionary."""
        return {
            "targetType": self.target_type,
            "targetId": self.target_id,
            "sourceType": self.source_type,
            "coordinates": self.coordinates,
            "timestamp": self.timestamp,
        }


@dataclass
class ValidationIssue:
    """Encapsulates a validation diagnostic or warning."""

    severity: str
    code: str
    message: str
    line_number: Optional[int] = None


@dataclass
class ValidationReport:
    """Aggregates all diagnostic issues found during validation."""

    is_valid: bool = True
    issues: list[ValidationIssue] = field(default_factory=list)

    def add_issue(
        self,
        severity: str,
        code: str,
        message: str,
        line_number: Optional[int] = None,
    ) -> None:
        """Append an issue and update validity flag."""
        if severity == "ERROR":
            self.is_valid = False
        self.issues.append(
            ValidationIssue(
                severity=severity,
                code=code,
                message=message,
                line_number=line_number,
            )
        )

    def has_code(self, code: str) -> bool:
        """Return True if any issue has the specified code."""
        return any(issue.code == code for issue in self.issues)

    @property
    def errors(self) -> list[ValidationIssue]:
        """Return only error level issues."""
        return [issue for issue in self.issues if issue.severity == "ERROR"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Return only warning level issues."""
        return [issue for issue in self.issues if issue.severity == "WARNING"]
