"""Schema validator for Bedrock block definitions enforcing 1.21+ / 1.26+ standards."""

import json
from pathlib import Path
from typing import Any

from packages.bedrock_block_validator.models import (
    RenderMethod,
    ValidationIssue,
    ValidationReport,
)


class BedrockBlockSchemaValidator:
    """Validates Bedrock block definitions against engine specifications."""

    VALID_RENDER_METHODS = {item.value for item in RenderMethod}
    DIRECTIONAL_FACES = {"up", "down", "north", "south", "east", "west"}

    @classmethod
    def validate_json_dict(cls, data: Any) -> ValidationReport:
        """Validate raw dictionary structure against Bedrock block schema.

        Args:
            data: Raw JSON deserialized object.

        Returns:
            ValidationReport detailing conformance and any violations.
        """
        issues: list[ValidationIssue] = []

        if not isinstance(data, dict):
            issues.append(
                ValidationIssue(
                    code="MALFORMED_ROOT",
                    message="Document must be a non-null JSON dictionary",
                )
            )
            return ValidationReport(is_valid=False, issues=issues)

        format_version = data.get("format_version")
        if not isinstance(format_version, str) or not format_version.strip():
            issues.append(
                ValidationIssue(
                    code="MISSING_FORMAT_VERSION",
                    message="Missing or invalid format_version string",
                )
            )

        block = data.get("minecraft:block")
        if not isinstance(block, dict):
            issues.append(
                ValidationIssue(
                    code="MISSING_BLOCK_ROOT",
                    message="Missing 'minecraft:block' root dictionary",
                )
            )
            return ValidationReport(is_valid=False, issues=issues)

        description = block.get("description")
        if not isinstance(description, dict):
            issues.append(
                ValidationIssue(
                    code="MISSING_DESCRIPTION",
                    message="Missing 'description' dictionary under 'minecraft:block'",
                )
            )
        else:
            identifier = description.get("identifier")
            if not isinstance(identifier, str) or ":" not in identifier:
                issues.append(
                    ValidationIssue(
                        code="INVALID_IDENTIFIER",
                        message="Identifier must be namespaced with colon format (e.g. namespace:name)",
                    )
                )

            if "isotropic" in description:
                issues.append(
                    ValidationIssue(
                        code="ISOTROPIC_IN_DESCRIPTION",
                        message="Property 'isotropic' is not allowed in 'description'. It must be declared inside 'minecraft:material_instances' face definitions.",
                    )
                )

        components = block.get("components")
        if not isinstance(components, dict):
            issues.append(
                ValidationIssue(
                    code="MISSING_COMPONENTS",
                    message="Missing 'components' dictionary under 'minecraft:block'",
                )
            )
            return ValidationReport(is_valid=False, issues=issues)

        mat_instances = components.get("minecraft:material_instances")
        if mat_instances is not None:
            if not isinstance(mat_instances, dict):
                issues.append(
                    ValidationIssue(
                        code="MALFORMED_MATERIAL_INSTANCES",
                        message="'minecraft:material_instances' must be a dictionary",
                    )
                )
            else:
                for face_key, inst_data in mat_instances.items():
                    if not isinstance(inst_data, dict):
                        issues.append(
                            ValidationIssue(
                                code="MALFORMED_INSTANCE_ENTRY",
                                message=f"Material instance '{face_key}' must be a dictionary",
                            )
                        )
                        continue

                    texture = inst_data.get("texture")
                    if not isinstance(texture, str) or not texture.strip():
                        issues.append(
                            ValidationIssue(
                                code="MISSING_TEXTURE",
                                message=f"Material instance '{face_key}' must specify a valid texture name",
                            )
                        )

                    render_method = inst_data.get("render_method")
                    if render_method is not None:
                        if render_method not in cls.VALID_RENDER_METHODS:
                            issues.append(
                                ValidationIssue(
                                    code="UNSUPPORTED_RENDER_METHOD",
                                    message=f"Render method '{render_method}' is unsupported. Allowed: {sorted(cls.VALID_RENDER_METHODS)}",
                                )
                            )

                        if face_key == "*" and render_method == "alpha_test":
                            issues.append(
                                ValidationIssue(
                                    code="INVALID_WILDCARD_ALPHA_TEST",
                                    message="Property 'minecraft:material_instances' contains invalid face specifier '*' with render method 'alpha_test'.",
                                )
                            )

                    isotropic = inst_data.get("isotropic")
                    if isotropic is not None and not isinstance(isotropic, bool):
                        issues.append(
                            ValidationIssue(
                                code="INVALID_ISOTROPIC_TYPE",
                                message=f"Material instance '{face_key}' property 'isotropic' must be a boolean",
                            )
                        )

                    ambient_occlusion = inst_data.get("ambient_occlusion")
                    if ambient_occlusion is not None and not isinstance(
                        ambient_occlusion, (int, float, bool)
                    ):
                        issues.append(
                            ValidationIssue(
                                code="INVALID_AMBIENT_OCCLUSION",
                                message=f"Material instance '{face_key}' property 'ambient_occlusion' must be numeric or boolean",
                            )
                        )

        geometry = components.get("minecraft:geometry")
        if geometry is not None:
            if isinstance(geometry, str):
                if not geometry.strip():
                    issues.append(
                        ValidationIssue(
                            code="EMPTY_GEOMETRY_STRING",
                            message="Geometry identifier string cannot be empty",
                        )
                    )
            elif isinstance(geometry, dict):
                geo_id = geometry.get("identifier")
                if not isinstance(geo_id, str) or not geo_id.strip():
                    issues.append(
                        ValidationIssue(
                            code="EMPTY_GEOMETRY_IDENTIFIER",
                            message="Geometry object must contain a valid non-empty 'identifier' string",
                        )
                    )
            else:
                issues.append(
                    ValidationIssue(
                        code="INVALID_GEOMETRY_TYPE",
                        message="Geometry component must be a string or dictionary",
                    )
                )

            if mat_instances is None:
                issues.append(
                    ValidationIssue(
                        code="GEOMETRY_WITHOUT_MATERIALS",
                        message="Blocks specifying 'minecraft:geometry' must also declare 'minecraft:material_instances'",
                    )
                )

        return ValidationReport(is_valid=len(issues) == 0, issues=issues)

    @classmethod
    def validate_compressed_basalt_dict(cls, data: Any) -> ValidationReport:
        """Validate compressed basalt specific requirements including isotropic faces.

        Args:
            data: Raw JSON deserialized object.

        Returns:
            ValidationReport with general and compressed basalt specific findings.
        """
        report = cls.validate_json_dict(data)
        if not report.is_valid:
            return report

        block = data["minecraft:block"]
        identifier = block["description"]["identifier"]
        if identifier != "custom:compressed_basalt":
            return ValidationReport(
                is_valid=False,
                issues=[
                    ValidationIssue(
                        code="UNEXPECTED_IDENTIFIER",
                        message=f"Expected identifier 'custom:compressed_basalt', got '{identifier}'",
                    )
                ],
            )

        mat_instances = block["components"].get("minecraft:material_instances", {})
        missing_faces = cls.DIRECTIONAL_FACES - set(mat_instances.keys())
        if missing_faces:
            return ValidationReport(
                is_valid=False,
                issues=[
                    ValidationIssue(
                        code="MISSING_DIRECTIONAL_FACES",
                        message=f"Missing explicit directional face definitions: {sorted(missing_faces)}",
                    )
                ],
            )

        up_face = mat_instances.get("up", {})
        down_face = mat_instances.get("down", {})

        issues: list[ValidationIssue] = []
        if not up_face.get("isotropic"):
            issues.append(
                ValidationIssue(
                    code="MISSING_TOP_ISOTROPIC",
                    message="Top face ('up') must configure 'isotropic: true' for natural basalt distribution",
                )
            )

        if not down_face.get("isotropic"):
            issues.append(
                ValidationIssue(
                    code="MISSING_BOTTOM_ISOTROPIC",
                    message="Bottom face ('down') must configure 'isotropic: true' for natural basalt distribution",
                )
            )

        return ValidationReport(is_valid=len(issues) == 0, issues=issues)

    @classmethod
    def validate_file(cls, file_path: str | Path) -> ValidationReport:
        """Load and validate block JSON definition from disk.

        Args:
            file_path: Filesystem path to the block JSON definition.

        Returns:
            ValidationReport containing verification outcome.
        """
        path = Path(file_path)
        if not path.is_file():
            return ValidationReport(
                is_valid=False,
                issues=[
                    ValidationIssue(
                        code="FILE_NOT_FOUND",
                        message=f"Block file does not exist: {path}",
                    )
                ],
            )

        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except json.JSONDecodeError as exc:
            return ValidationReport(
                is_valid=False,
                issues=[
                    ValidationIssue(
                        code="JSON_DECODE_ERROR",
                        message=f"Failed to parse JSON file {path.name}: {exc}",
                    )
                ],
            )

        return cls.validate_compressed_basalt_dict(data)
