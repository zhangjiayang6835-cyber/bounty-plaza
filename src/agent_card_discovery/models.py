"""
Data models, deterministic normalization, and validation rules for Agent Cards.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .canonical_url import canonicalize_url
from .errors import (
    InvalidFieldTypeError,
    MissingFieldError,
    SecurityViolationError,
)

FORBIDDEN_SUBSTRINGS = (
    "private_key",
    "private key",
    "seed phrase",
    "api_key",
    "secret",
)


def normalize_string_list(items: Any, field_name: str) -> list[str]:
    """
    Trim, deduplicate, and sort a list of strings deterministically.
    """
    if items is None:
        return []
    if isinstance(items, str):
        items = [items]
    if not isinstance(items, (list, tuple, set)):
        raise InvalidFieldTypeError(field_name, "list of strings", type(items).__name__)

    cleaned: set[str] = set()
    for item in items:
        if not isinstance(item, str):
            raise InvalidFieldTypeError(
                field_name, "string element", type(item).__name__
            )
        trimmed = item.strip()
        if trimmed:
            cleaned.add(trimmed)
    return sorted(cleaned)


@dataclass
class AgentInterface:
    """Represents a supported transport/protocol interface."""

    url: str
    protocol_binding: str = "HTTP+JSON"
    protocol_version: str = "1.0"

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], context_url: str | None = None
    ) -> AgentInterface:
        if not isinstance(data, dict):
            raise InvalidFieldTypeError(
                "supportedInterfaces entry",
                "dict",
                type(data).__name__,
                url=context_url,
            )

        raw_url = data.get("url")
        if not raw_url or not isinstance(raw_url, str):
            raise MissingFieldError("url in supportedInterfaces", url=context_url)

        canonical_url = canonicalize_url(raw_url)

        binding = (
            data.get("protocolBinding") or data.get("protocol_binding") or "HTTP+JSON"
        )
        # Spec version fallback to "1.0"
        version = data.get("protocolVersion") or data.get("protocol_version") or "1.0"

        return cls(
            url=canonical_url,
            protocol_binding=str(binding).strip(),
            protocol_version=str(version).strip(),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "url": self.url,
            "protocolBinding": self.protocol_binding,
            "protocolVersion": self.protocol_version,
        }


@dataclass
class AgentSkill:
    """Represents an agent capability/skill."""

    id: str
    name: str
    description: str
    tags: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    input_modes: list[str] = field(
        default_factory=lambda: ["application/json", "text/plain"]
    )
    output_modes: list[str] = field(
        default_factory=lambda: ["application/json", "text/plain"]
    )

    @classmethod
    def from_dict(
        cls, data: dict[str, Any] | str, context_url: str | None = None
    ) -> AgentSkill:
        if isinstance(data, str):
            trimmed = data.strip()
            if not trimmed:
                raise MissingFieldError("skill id", url=context_url)
            return cls(
                id=trimmed,
                name=trimmed.replace("-", " ").title(),
                description=f"Automated execution for skill {trimmed}",
                tags=[trimmed],
            )

        if not isinstance(data, dict):
            raise InvalidFieldTypeError(
                "skill entry", "dict or str", type(data).__name__, url=context_url
            )

        skill_id = str(data.get("id") or "").strip()
        name = str(data.get("name") or "").strip()
        desc = str(data.get("description") or "").strip()

        if not skill_id:
            raise MissingFieldError("skill id", url=context_url)
        if not name:
            raise MissingFieldError("skill name", url=context_url)
        if not desc:
            raise MissingFieldError("skill description", url=context_url)

        tags = normalize_string_list(data.get("tags") or [skill_id], "tags")
        examples = normalize_string_list(data.get("examples") or [], "examples")

        raw_in = (
            data.get("inputModes")
            or data.get("input_modes")
            or ["application/json", "text/plain"]
        )
        raw_out = (
            data.get("outputModes")
            or data.get("output_modes")
            or ["application/json", "text/plain"]
        )

        input_modes = normalize_string_list(raw_in, "inputModes")
        output_modes = normalize_string_list(raw_out, "outputModes")

        return cls(
            id=skill_id,
            name=name,
            description=desc,
            tags=tags,
            examples=examples,
            input_modes=input_modes,
            output_modes=output_modes,
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tags": sorted(self.tags),
        }
        if self.examples:
            result["examples"] = self.examples
        if self.input_modes:
            result["inputModes"] = self.input_modes
        if self.output_modes:
            result["outputModes"] = self.output_modes
        return result


@dataclass
class AgentCard:
    """Canonical model for an Agent Card."""

    name: str
    description: str
    version: str
    capabilities: dict[str, Any]
    supported_interfaces: list[AgentInterface]
    skills: list[AgentSkill]
    default_input_modes: list[str] = field(
        default_factory=lambda: ["application/json", "text/plain"]
    )
    default_output_modes: list[str] = field(
        default_factory=lambda: ["application/json", "text/plain"]
    )
    documentation_url: str | None = None
    icon_url: str | None = None
    provider: dict[str, Any] | None = None

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], context_url: str | None = None
    ) -> AgentCard:
        if not isinstance(data, dict):
            raise InvalidFieldTypeError(
                "agent_card", "dict", type(data).__name__, url=context_url
            )

        # 1. Check for forbidden security material
        serialized = json.dumps(data, sort_keys=True).lower()
        for forbidden in FORBIDDEN_SUBSTRINGS:
            if forbidden in serialized:
                raise SecurityViolationError(
                    f"Agent card contains forbidden material: '{forbidden}'",
                    url=context_url,
                )

        # 2. Required fields validation
        name = str(data.get("name") or "").strip()
        if not name:
            raise MissingFieldError("name", url=context_url)

        description = str(data.get("description") or "").strip()
        if not description:
            raise MissingFieldError("description", url=context_url)

        version = str(data.get("version") or "").strip()
        if not version:
            raise MissingFieldError("version", url=context_url)

        # 3. Capabilities normalization
        raw_caps = data.get("capabilities")
        if raw_caps is None:
            raise MissingFieldError("capabilities", url=context_url)

        if isinstance(raw_caps, list):
            # Deterministic list-to-dict or normalized string list
            caps_dict = {
                str(k).strip(): True
                for k in normalize_string_list(raw_caps, "capabilities")
            }
        elif isinstance(raw_caps, dict):
            caps_dict = {str(k).strip(): v for k, v in sorted(raw_caps.items())}
        else:
            raise InvalidFieldTypeError(
                "capabilities", "dict or list", type(raw_caps).__name__, url=context_url
            )

        # 4. Interfaces validation & normalization
        raw_interfaces = (
            data.get("supportedInterfaces")
            or data.get("supported_interfaces")
            or data.get("interfaces")
        )
        if not raw_interfaces or not isinstance(raw_interfaces, list):
            raise MissingFieldError(
                "supportedInterfaces",
                message="Agent Card must declare at least one interface in 'supportedInterfaces'",
                url=context_url,
            )

        interfaces = [
            AgentInterface.from_dict(item, context_url=context_url)
            for item in raw_interfaces
        ]
        # Sort interfaces deterministically by URL
        interfaces.sort(key=lambda x: x.url)

        # 5. Skills validation & normalization
        raw_skills = data.get("skills")
        if not isinstance(raw_skills, list) or not raw_skills:
            raise MissingFieldError(
                "skills",
                message="Agent Card must declare a non-empty list of 'skills'",
                url=context_url,
            )

        skills = [
            AgentSkill.from_dict(item, context_url=context_url) for item in raw_skills
        ]
        # Sort skills deterministically by ID
        skills.sort(key=lambda s: s.id)

        # 6. Input/Output Modes
        default_in = normalize_string_list(
            data.get("defaultInputModes")
            or data.get("default_input_modes")
            or ["application/json", "text/plain"],
            "defaultInputModes",
        )
        default_out = normalize_string_list(
            data.get("defaultOutputModes")
            or data.get("default_output_modes")
            or ["application/json", "text/plain"],
            "defaultOutputModes",
        )
        if not default_in:
            raise MissingFieldError("defaultInputModes", url=context_url)
        if not default_out:
            raise MissingFieldError("defaultOutputModes", url=context_url)

        # 7. Optional metadata URLs
        doc_url = data.get("documentationUrl") or data.get("documentation_url")
        canonical_doc_url = canonicalize_url(doc_url) if doc_url else None

        icon_url = data.get("iconUrl") or data.get("icon_url")
        canonical_icon_url = canonicalize_url(icon_url) if icon_url else None

        provider = (
            data.get("provider") if isinstance(data.get("provider"), dict) else None
        )

        return cls(
            name=name,
            description=description,
            version=version,
            capabilities=caps_dict,
            supported_interfaces=interfaces,
            skills=skills,
            default_input_modes=default_in,
            default_output_modes=default_out,
            documentation_url=canonical_doc_url,
            icon_url=canonical_icon_url,
            provider=provider,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to standard canonical A2A JSON representation."""
        res: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "capabilities": self.capabilities,
            "defaultInputModes": self.default_input_modes,
            "defaultOutputModes": self.default_output_modes,
            "supportedInterfaces": [i.to_dict() for i in self.supported_interfaces],
            "skills": [s.to_dict() for s in self.skills],
        }
        if self.provider:
            res["provider"] = self.provider
        if self.documentation_url:
            res["documentationUrl"] = self.documentation_url
        if self.icon_url:
            res["iconUrl"] = self.icon_url
        return res
