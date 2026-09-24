"""Validator enforcing acceptance standards for A2A Agent Card definitions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AgentCardValidator:
    """Enforces schema compliance and security boundary validation on agent cards."""

    CANONICAL_NAME = "Agent Bounties"
    REQUIRED_BINDING = "https://agentbounties.app/docs/a2a-direct-api-binding-v1"
    CANONICAL_API_PREFIX = "https://api.agentbounties.app/"

    REQUIRED_SKILLS = frozenset(
        {
            "discover-funded-work",
            "plan-bounty-claim",
            "submit-bounty-evidence",
            "check-bounty-settlement",
            "post-bounty",
        }
    )

    FORBIDDEN_PHRASES = (
        "private_key",
        "private key",
        "seed phrase",
        "api_key",
        "secret",
    )

    REQUIRED_PHRASES = (
        "canonical",
        "claimable",
        "bountysettled",
    )

    @classmethod
    def validate_file(cls, file_path: str) -> tuple[bool, list[str]]:
        """Validate agent card JSON file against specification invariants.

        Args:
            file_path: Path string to target JSON fixture file.

        Returns:
            Tuple consisting of validity boolean and list of error descriptions.
        """
        path = Path(file_path)
        if not path.is_file():
            return False, [f"File not found: {file_path}"]

        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
        except json.JSONDecodeError as exc:
            return False, [f"Invalid JSON syntax in {file_path}: {exc}"]

        return cls.validate_dict(data)

    @classmethod
    def validate_dict(cls, data: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate agent card dictionary against specification invariants.

        Args:
            data: Parsed JSON agent card dictionary.

        Returns:
            Tuple consisting of validity boolean and list of error descriptions.
        """
        errors = []

        if data.get("name") != cls.CANONICAL_NAME:
            errors.append(
                f"Agent Card name must be '{cls.CANONICAL_NAME}', got '{data.get('name')}'"
            )

        if not str(data.get("description", "")).strip():
            errors.append("Agent Card description is required")

        if not str(data.get("version", "")).strip():
            errors.append("Agent Card version is required")

        if not isinstance(data.get("capabilities"), dict):
            errors.append("Agent Card capabilities must be an object")

        for mode_key in ("defaultInputModes", "defaultOutputModes"):
            mode_val = data.get(mode_key)
            if not isinstance(mode_val, list) or not mode_val:
                errors.append(f"Agent Card {mode_key} must be a non-empty array")

        interfaces = data.get("supportedInterfaces")
        if not isinstance(interfaces, list) or not interfaces:
            errors.append("Agent Card must declare at least one supported interface")
        else:
            cls._validate_interfaces(interfaces, errors)

        if "protocolVersion" in data:
            errors.append(
                "protocolVersion belongs on interfaces, not the Agent Card root"
            )

        skills = data.get("skills")
        if not isinstance(skills, list):
            errors.append("Agent Card skills must be an array")
        else:
            cls._validate_skills(skills, errors)

        serialized = json.dumps(data, sort_keys=True).lower()
        cls._validate_content_boundaries(serialized, errors)

        is_valid = len(errors) == 0
        return is_valid, errors

    @classmethod
    def _validate_interfaces(
        cls, interfaces: list[Any], errors: list[str]
    ) -> None:
        """Inspect declared interface objects for binding correctness.

        Args:
            interfaces: Collection of interface dictionaries.
            errors: Mutable accumulator for error messages.
        """
        for index, item in enumerate(interfaces):
            if not isinstance(item, dict):
                errors.append(f"Interface at index {index} is not an object")
                continue
            url = str(item.get("url", ""))
            if not url.startswith(cls.CANONICAL_API_PREFIX):
                errors.append(
                    f"Interface URL '{url}' must start with {cls.CANONICAL_API_PREFIX}"
                )
            if item.get("protocolVersion") != "1.0":
                errors.append(
                    f"Interface protocolVersion must be '1.0', got '{item.get('protocolVersion')}'"
                )
            if item.get("protocolBinding") != cls.REQUIRED_BINDING:
                errors.append(
                    f"Interface protocolBinding must match '{cls.REQUIRED_BINDING}'"
                )

    @classmethod
    def _validate_skills(cls, skills: list[Any], errors: list[str]) -> None:
        """Inspect skill declarations and ensure required identifiers are present.

        Args:
            skills: Collection of declared skill dictionaries.
            errors: Mutable accumulator for error messages.
        """
        declared_ids = set()
        for index, skill in enumerate(skills):
            if not isinstance(skill, dict):
                errors.append(f"Skill at index {index} is not an object")
                continue
            for required_field in ("id", "name", "description", "tags"):
                val = skill.get(required_field)
                if val is None or val == "" or val == []:
                    errors.append(
                        f"Skill '{skill.get('id', index)}' missing field '{required_field}'"
                    )
            skill_id = str(skill.get("id", ""))
            if skill_id:
                declared_ids.add(skill_id)

        missing = cls.REQUIRED_SKILLS - declared_ids
        if missing:
            errors.append(
                f"Agent Card is missing mandatory skills: {sorted(missing)}"
            )

    @classmethod
    def _validate_content_boundaries(
        cls, serialized_lower: str, errors: list[str]
    ) -> None:
        """Validate safety phrases and required evidence terms in serialization.

        Args:
            serialized_lower: Lowercase JSON serialization string.
            errors: Mutable accumulator for error messages.
        """
        for forbidden in cls.FORBIDDEN_PHRASES:
            if forbidden in serialized_lower:
                errors.append(
                    f"Agent Card exposes forbidden credential material: {forbidden}"
                )

        for required in cls.REQUIRED_PHRASES:
            if required not in serialized_lower:
                errors.append(
                    f"Agent Card must preserve the '{required}' evidence boundary"
                )
