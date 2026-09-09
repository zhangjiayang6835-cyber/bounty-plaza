"""Bedrock block schema validator and resource pack sound alignment checker."""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Set
from packages.bedrock_block_schema.models import ValidationReport


PROHIBITED_DESCRIPTION_FIELDS: Set[str] = {
    "sound",
    "register_to_creative_menu",
    "is_experimental",
}

VALID_CATEGORIES: Set[str] = {
    "construction",
    "nature",
    "equipment",
    "items",
    "none",
    "commands",
}

VALID_RENDER_METHODS: Set[str] = {
    "opaque",
    "blend",
    "alpha_test",
    "alpha_test_single_sided",
    "double_sided",
}


class BlockSchemaValidator:
    """Validator for Bedrock block definitions and associated resource pack configs."""

    def __init__(self, target_format: str = "1.26.30") -> None:
        """Initialize validator with target Bedrock format version."""
        self.target_format = target_format

    def validate_file(self, file_path: str) -> ValidationReport:
        """Load and validate a block definition JSON file from disk."""
        path_obj = Path(file_path)
        if not path_obj.exists():
            error_msg = f"Block file does not exist: {file_path}"
            report = ValidationReport(
                identifier="unknown",
                format_version=self.target_format,
                is_valid=False,
            )
            report.add_error("file", error_msg)
            return report

        try:
            with open(path_obj, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except json.JSONDecodeError as err:
            parse_err = f"Failed to parse JSON: {err}"
            report = ValidationReport(
                identifier="unknown",
                format_version=self.target_format,
                is_valid=False,
            )
            report.add_error("json", parse_err)
            return report

        return self.validate_dict(data)

    def validate_dict(self, data: Dict[str, Any]) -> ValidationReport:
        """Validate an in-memory block definition structure against target schema."""
        format_version = str(data.get("format_version", ""))
        block_body = data.get("minecraft:block", {})

        desc = block_body.get("description", {}) if isinstance(block_body, dict) else {}
        identifier = str(desc.get("identifier", "unknown")) if isinstance(desc, dict) else "unknown"

        report = ValidationReport(
            identifier=identifier,
            format_version=format_version,
            is_valid=True,
        )

        if not format_version:
            report.add_error("format_version", "Missing format_version property in block JSON")

        if not isinstance(block_body, dict) or not block_body:
            report.add_error("minecraft:block", "Missing or empty minecraft:block root object")
            return report

        self._validate_description(desc, format_version, report)

        components = block_body.get("components", {})
        if isinstance(components, dict):
            self._validate_components(components, report)
        else:
            report.add_error(
                "minecraft:block.components",
                "Components section must be a dictionary",
            )

        return report

    def _validate_description(
        self,
        desc: Any,
        format_version: str,
        report: ValidationReport,
    ) -> None:
        """Verify description fields, disallowing sound under modern format versions."""
        if not isinstance(desc, dict) or not desc:
            report.add_error(
                "minecraft:block.description",
                "Description object is missing or invalid",
            )
            return

        identifier = desc.get("identifier")
        if not identifier or not isinstance(identifier, str):
            report.add_error("minecraft:block.description.identifier", "Identifier is required")
        elif ":" not in identifier:
            report.add_warning(
                "minecraft:block.description.identifier",
                "Identifier lacks namespace prefix",
            )

        menu_category = desc.get("menu_category")
        if isinstance(menu_category, dict):
            category = menu_category.get("category")
            if category and category not in VALID_CATEGORIES:
                cat_msg = f"Unknown menu category: {category}"
                report.add_warning("minecraft:block.description.menu_category.category", cat_msg)

        for prohibited in PROHIBITED_DESCRIPTION_FIELDS:
            if prohibited in desc:
                err_msg = (
                    f"Property '{prohibited}' is not allowed inside "
                    f"'description' object under format_version {format_version}."
                )
                report.add_error(f"minecraft:block.description.{prohibited}", err_msg)

    def _validate_components(
        self,
        components: Dict[str, Any],
        report: ValidationReport,
    ) -> None:
        """Validate core block components for physical and rendering properties."""
        if "minecraft:destructible_by_mining" in components:
            mining = components["minecraft:destructible_by_mining"]
            mining_path = "minecraft:block.components.minecraft:destructible_by_mining"
            if isinstance(mining, dict):
                destroy_time = mining.get("seconds_to_destroy")
                if destroy_time is not None and not isinstance(destroy_time, (int, float)):
                    report.add_error(
                        f"{mining_path}.seconds_to_destroy",
                        "seconds_to_destroy must be a numeric value",
                    )
            elif not isinstance(mining, bool):
                report.add_error(
                    mining_path,
                    "minecraft:destructible_by_mining must be boolean or object",
                )

        if "minecraft:material_instances" in components:
            materials = components["minecraft:material_instances"]
            if isinstance(materials, dict):
                for instance_name, instance_data in materials.items():
                    if isinstance(instance_data, dict):
                        render_method = instance_data.get("render_method")
                        if render_method and render_method not in VALID_RENDER_METHODS:
                            rend_err = f"Invalid render_method '{render_method}' in {instance_name}"
                            inst_path = (
                                f"minecraft:block.components.minecraft:material_instances."
                                f"{instance_name}"
                            )
                            report.add_warning(inst_path, rend_err)


class ResourcePackSoundResolver:
    """Verifies that block sound profiles are registered in client resource pack configs."""

    def __init__(self, rp_blocks_path: str = "RP/blocks.json") -> None:
        """Initialize resolver with path to RP blocks.json."""
        self.rp_blocks_path = Path(rp_blocks_path)

    def load_definitions(self) -> Dict[str, Any]:
        """Load block definitions from RP/blocks.json."""
        if not self.rp_blocks_path.exists():
            return {}
        try:
            with open(self.rp_blocks_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
                if isinstance(data, dict):
                    return data
                return {}
        except json.JSONDecodeError:
            return {}

    def resolve_sound(self, identifier: str) -> Optional[str]:
        """Look up the configured sound profile for a given block identifier."""
        data = self.load_definitions()
        block_entry = data.get(identifier)
        if isinstance(block_entry, dict):
            sound_val = block_entry.get("sound")
            if isinstance(sound_val, str):
                return sound_val
        return None

    def verify_block_sound(
        self,
        identifier: str,
        expected_sound: str = "stone",
    ) -> ValidationReport:
        """Verify that a block has the expected sound category mapped in RP/blocks.json."""
        report = ValidationReport(
            identifier=identifier,
            format_version="resource_pack",
            is_valid=True,
        )

        if not self.rp_blocks_path.exists():
            missing_rp = f"Resource pack blocks file not found at {self.rp_blocks_path}"
            report.add_error("rp_blocks", missing_rp)
            return report

        definitions = self.load_definitions()
        if identifier not in definitions:
            missing_block = f"Block {identifier} is not defined in {self.rp_blocks_path}"
            report.add_error("identifier", missing_block)
            return report

        entry = definitions[identifier]
        if not isinstance(entry, dict):
            report.add_error("entry", f"Block entry for {identifier} must be a JSON object")
            return report

        sound = entry.get("sound")
        if not sound:
            missing_snd = f"Block {identifier} does not declare a 'sound' mapping in resource pack"
            report.add_error("sound", missing_snd)
        elif sound != expected_sound:
            mismatch_snd = f"Block sound mismatch: expected '{expected_sound}', found '{sound}'"
            report.add_error("sound", mismatch_snd)

        return report
