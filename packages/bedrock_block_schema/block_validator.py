"""Bedrock block schema validator and normalizer module."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Set, Tuple


class BlockFace(str, Enum):
    """Enumeration of valid Bedrock block face identifiers."""

    UP = "up"
    DOWN = "down"
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    WILDCARD = "*"


class RenderMethod(str, Enum):
    """Enumeration of valid Bedrock material instance render methods."""

    OPAQUE = "opaque"
    DOUBLE_SIDED = "double_sided"
    BLEND = "blend"
    ALPHA_TEST = "alpha_test"


@dataclass
class ValidationResult:
    """Result of validating a Bedrock block definition against modern schemas."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    format_version: str = "1.21.40"
    identifier: str = ""
    material_instances: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    has_seamless_outline: bool = False


class BedrockBlockValidator:
    """Validates and normalizes Minecraft Bedrock block JSON definitions."""

    SUPPORTED_VERSIONS: Set[str] = {
        "1.21.40",
        "1.21.50",
        "1.21.60",
        "1.26.0",
        "1.26.10",
    }

    CUBE_FACES: Set[str] = {
        BlockFace.UP.value,
        BlockFace.DOWN.value,
        BlockFace.NORTH.value,
        BlockFace.SOUTH.value,
        BlockFace.EAST.value,
        BlockFace.WEST.value,
    }

    STANDARD_ORIGIN: List[float] = [-8.0, 0.0, -8.0]
    STANDARD_SIZE: List[float] = [16.0, 16.0, 16.0]

    @classmethod
    def is_valid_render_method(cls, method: str) -> bool:
        """Check if a render method is supported by the Bedrock block schema.

        Args:
            method: Name of the render method.

        Returns:
            True if method is a supported render method enum value.
        """
        valid_methods = {item.value for item in RenderMethod}
        is_supported = method in valid_methods
        return is_supported

    @classmethod
    def validate_material_instance_entry(
        cls,
        face_name: str,
        entry: Dict[str, Any],
        format_version: str,
    ) -> List[str]:
        """Validate a single material instance configuration.

        Args:
            face_name: The face name or material instance key.
            entry: Dictionary containing the material instance configuration.
            format_version: The Bedrock schema format version.

        Returns:
            A list of validation error messages.
        """
        errors: List[str] = []
        if not isinstance(entry, dict):
            errors.append(f"Material instance '{face_name}' must be an object.")
            return errors

        texture = entry.get("texture")
        if not texture or not isinstance(texture, str):
            errors.append(f"Material instance '{face_name}' is missing a valid 'texture' string.")

        render_method = entry.get("render_method", RenderMethod.OPAQUE.value)
        if not cls.is_valid_render_method(render_method):
            errors.append(
                f"Render method '{render_method}' is unsupported under schema {format_version}."
            )

        if "isotropic" in entry and not isinstance(entry["isotropic"], bool):
            errors.append(f"Material instance '{face_name}' 'isotropic' must be a boolean.")

        if "face_dimming" in entry and not isinstance(entry["face_dimming"], bool):
            errors.append(f"Material instance '{face_name}' 'face_dimming' must be a boolean.")

        if "ambient_occlusion" in entry and not isinstance(
            entry["ambient_occlusion"], (bool, float, int)
        ):
            errors.append(
                f"Material instance '{face_name}' 'ambient_occlusion' must be a boolean or number."
            )

        return errors

    @classmethod
    def validate_material_instances(
        cls,
        instances: Any,
        format_version: str,
        is_directional: bool,
    ) -> Tuple[List[str], List[str]]:
        """Validate the minecraft:material_instances component dictionary.

        Args:
            instances: The material_instances object from the block definition.
            format_version: Bedrock schema format version.
            is_directional: Whether the block requires face-specific textures.

        Returns:
            A tuple of (errors, warnings).
        """
        errors: List[str] = []
        warnings: List[str] = []

        if not isinstance(instances, dict) or not instances:
            errors.append("Component 'minecraft:material_instances' must be a non-empty object.")
            result_tuple = (errors, warnings)
            return result_tuple

        keys = set(instances.keys())

        if is_directional and BlockFace.WILDCARD.value in keys:
            errors.append(
                "Property 'minecraft:material_instances' contains invalid face definition '*'."
            )

        valid_face_names = cls.CUBE_FACES.union({BlockFace.WILDCARD.value})
        unknown_faces = keys - valid_face_names
        for face in sorted(unknown_faces):
            warnings.append(
                f"Custom material target '{face}' not in standard directional face set."
            )

        for face, conf in instances.items():
            errors.extend(cls.validate_material_instance_entry(face, conf, format_version))

        if is_directional:
            missing_faces = cls.CUBE_FACES - keys
            if missing_faces:
                errors.append(
                    f"Directional block missing required face definitions: {sorted(missing_faces)}."
                )

        result_pair = (errors, warnings)
        return result_pair

    @classmethod
    def validate_selection_and_collision(
        cls,
        components: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """Validate selection box and collision box for seamless outline rendering.

        Args:
            components: The components dictionary of the block.

        Returns:
            Tuple of (has_seamless_outline, error_list).
        """
        errors: List[str] = []
        sel_box = components.get("minecraft:selection_box")

        if not isinstance(sel_box, dict):
            errors.append("Missing or invalid 'minecraft:selection_box' component.")
            res_fail = (False, errors)
            return res_fail

        origin = sel_box.get("origin")
        size = sel_box.get("size")

        if not isinstance(origin, list) or len(origin) != 3:
            errors.append("'minecraft:selection_box.origin' must be a 3-element numeric list.")
            res_fail = (False, errors)
            return res_fail

        if not isinstance(size, list) or len(size) != 3:
            errors.append("'minecraft:selection_box.size' must be a 3-element numeric list.")
            res_fail = (False, errors)
            return res_fail

        is_origin_aligned = [float(val) for val in origin] == cls.STANDARD_ORIGIN
        is_size_aligned = [float(val) for val in size] == cls.STANDARD_SIZE

        if not is_origin_aligned or not is_size_aligned:
            errors.append(
                f"Selection box [{origin}, {size}] diverges from standard unit cube bounds."
            )
            res_fail = (False, errors)
            return res_fail

        res_ok = (True, errors)
        return res_ok

    @classmethod
    def _parse_root_nodes(
        cls,
        block_def: Dict[str, Any],
    ) -> Tuple[str, str, Dict[str, Any], List[str]]:
        """Extract and validate top-level structural nodes of a block definition.

        Args:
            block_def: Parsed block definition dictionary.

        Returns:
            Tuple of (format_version, identifier, components, errors).
        """
        errors: List[str] = []
        version = block_def.get("format_version", "")
        if not version:
            errors.append("Block definition missing required 'format_version'.")

        block_node = block_def.get("minecraft:block")
        if not isinstance(block_node, dict):
            errors.append("Block definition missing required 'minecraft:block' object.")
            res_no_block = (version, "", {}, errors)
            return res_no_block

        desc = block_node.get("description", {})
        identifier = desc.get("identifier", "")
        if not identifier:
            errors.append("Block description missing required 'identifier'.")

        components = block_node.get("components", {})
        if not isinstance(components, dict):
            errors.append("Block node missing required 'components' object.")
            res_no_comps = (version, identifier, {}, errors)
            return res_no_comps

        res_ok = (version, identifier, components, errors)
        return res_ok

    @classmethod
    def validate_block_definition(
        cls,
        block_def: Dict[str, Any],
        is_directional: bool = True,
    ) -> ValidationResult:
        """Validate a complete Bedrock block definition against modern schemas.

        Args:
            block_def: Complete parsed JSON block definition.
            is_directional: Whether block expects directional multi-face texturing.

        Returns:
            A ValidationResult dataclass containing diagnostics and status.
        """
        if not isinstance(block_def, dict):
            return ValidationResult(
                is_valid=False,
                errors=["Root block definition must be a JSON object."],
            )

        ver, ident, comps, errors = cls._parse_root_nodes(block_def)
        if not comps:
            return ValidationResult(
                is_valid=False,
                errors=errors,
                format_version=ver,
                identifier=ident,
            )

        instances = comps.get("minecraft:material_instances")
        mat_errs, warnings = cls.validate_material_instances(instances, ver, is_directional)
        errors.extend(mat_errs)

        if not comps.get("minecraft:geometry"):
            errors.append("Block definition missing required 'minecraft:geometry' component.")

        has_outline, outline_errors = cls.validate_selection_and_collision(comps)
        errors.extend(outline_errors)

        valid = len(errors) == 0
        final_result = ValidationResult(
            is_valid=valid,
            errors=errors,
            warnings=warnings,
            format_version=ver,
            identifier=ident,
            material_instances=instances if isinstance(instances, dict) else {},
            has_seamless_outline=has_outline and valid,
        )
        return final_result

    @classmethod
    def _resolve_face_texture(cls, face: str) -> str:
        """Resolve directional texture identifier for a specific face.

        Args:
            face: The cube face string.

        Returns:
            The corresponding texture asset key.
        """
        base_prefix = "void_crystal_ore"
        target_suffix = "side"
        if face == "up":
            target_suffix = "top"
        elif face == "down":
            target_suffix = "bottom"

        resolved_name = f"{base_prefix}_{target_suffix}"
        return resolved_name

    @classmethod
    def _build_default_components(
        cls,
        render_method: str,
    ) -> Dict[str, Any]:
        """Construct standard conforming block components.

        Args:
            render_method: The render method for material instances.

        Returns:
            Dictionary of conforming Bedrock block components.
        """
        instances: Dict[str, Dict[str, Any]] = {}
        for face in sorted(cls.CUBE_FACES):
            instances[face] = {
                "texture": cls._resolve_face_texture(face),
                "render_method": render_method,
                "face_dimming": True,
                "ambient_occlusion": True,
                "isotropic": False,
            }

        comps: Dict[str, Any] = {
            "minecraft:geometry": "geometry.void_crystal_ore",
            "minecraft:material_instances": instances,
            "minecraft:selection_box": {
                "origin": list(cls.STANDARD_ORIGIN),
                "size": list(cls.STANDARD_SIZE),
            },
            "minecraft:collision_box": {
                "origin": list(cls.STANDARD_ORIGIN),
                "size": list(cls.STANDARD_SIZE),
            },
            "minecraft:destructible_by_mining": {"seconds_to_destroy": 3.0},
            "minecraft:destructible_by_explosion": {"explosion_resistance": 3.0},
            "minecraft:friction": 0.6,
            "minecraft:light_emission": 3,
            "minecraft:map_color": "#4A0E4E",
        }
        return comps

    @classmethod
    def migrate_definition(
        cls,
        legacy_def: Dict[str, Any],
        default_render_method: str = RenderMethod.ALPHA_TEST.value,
    ) -> Dict[str, Any]:
        """Normalize and migrate legacy or malformed block JSON to modern schema.

        Args:
            legacy_def: Existing block definition.
            default_render_method: Desired render method for material instances.

        Returns:
            A compliant Bedrock 1.21.40+ block definition dictionary.
        """
        old_block = legacy_def.get("minecraft:block", {})
        old_desc = old_block.get("description", {})
        identifier = old_desc.get("identifier", "custom:void_crystal_ore")
        category = old_desc.get(
            "menu_category",
            {"category": "nature", "group": "itemGroup.name.ore"},
        )

        clean_method = (
            default_render_method
            if cls.is_valid_render_method(default_render_method)
            else RenderMethod.ALPHA_TEST.value
        )

        components = cls._build_default_components(clean_method)
        old_comps = old_block.get("components", {})
        for key in (
            "minecraft:destructible_by_mining",
            "minecraft:destructible_by_explosion",
            "minecraft:friction",
            "minecraft:light_emission",
            "minecraft:map_color",
        ):
            if key in old_comps:
                components[key] = old_comps[key]

        migrated_dict: Dict[str, Any] = {
            "format_version": "1.21.40",
            "minecraft:block": {
                "description": {
                    "identifier": identifier,
                    "menu_category": category,
                },
                "components": components,
            },
        }
        return migrated_dict
