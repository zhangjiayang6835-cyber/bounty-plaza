"""Bedrock geometry builder and outline validation module."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set, Tuple


@dataclass
class GeometryDefinition:
    """Represents a validated Bedrock geometry definition for block rendering."""

    identifier: str
    texture_size: Tuple[int, int] = (16, 16)
    origin: List[float] = field(default_factory=lambda: [-8.0, 0.0, -8.0])
    size: List[float] = field(default_factory=lambda: [16.0, 16.0, 16.0])
    bones: List[Dict[str, Any]] = field(default_factory=list)
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)


class BlockGeometryBuilder:
    """Builds and validates Minecraft Bedrock block geometry definitions."""

    REQUIRED_FACES: Set[str] = {
        "north",
        "east",
        "south",
        "west",
        "up",
        "down",
    }

    UNIT_ORIGIN: List[float] = [-8.0, 0.0, -8.0]
    UNIT_SIZE: List[float] = [16.0, 16.0, 16.0]

    @classmethod
    def create_unit_cube_geometry(
        cls,
        identifier: str = "geometry.void_crystal_ore",
        texture_width: int = 16,
        texture_height: int = 16,
    ) -> Dict[str, Any]:
        """Generate a complete conforming Bedrock block geometry JSON object.

        Args:
            identifier: The unique geometry identifier.
            texture_width: Texture map width in pixels.
            texture_height: Texture map height in pixels.

        Returns:
            Dictionary formatted according to Bedrock format_version 1.12.0.
        """
        uv_mapping: Dict[str, Dict[str, Any]] = {}
        for face in sorted(cls.REQUIRED_FACES):
            uv_mapping[face] = {
                "uv": [0, 0],
                "uv_size": [16, 16],
                "material_instance": face,
            }

        return {
            "format_version": "1.12.0",
            "minecraft:geometry": [
                {
                    "description": {
                        "identifier": identifier,
                        "texture_width": texture_width,
                        "texture_height": texture_height,
                        "visible_bounds_width": 1.0,
                        "visible_bounds_height": 1.0,
                        "visible_bounds_offset": [0.0, 0.5, 0.0],
                    },
                    "bones": [
                        {
                            "name": "root",
                            "pivot": [0.0, 0.0, 0.0],
                            "cubes": [
                                {
                                    "origin": list(cls.UNIT_ORIGIN),
                                    "size": list(cls.UNIT_SIZE),
                                    "uv": uv_mapping,
                                }
                            ],
                        }
                    ],
                }
            ],
        }

    @classmethod
    def _validate_cubes(
        cls,
        cubes: List[Dict[str, Any]],
    ) -> Tuple[bool, List[str]]:
        """Validate cubes array within a bone for alignment and UV mapping.

        Args:
            cubes: List of cube definitions from a geometry bone.

        Returns:
            Tuple of (is_valid, errors).
        """
        errors: List[str] = []
        if not isinstance(cubes, list) or not cubes:
            errors.append("Bone must contain at least one cube definition.")
            return False, errors

        root_cube = cubes[0]
        origin = root_cube.get("origin")
        size = root_cube.get("size")

        if origin != cls.UNIT_ORIGIN or size != cls.UNIT_SIZE:
            errors.append(
                f"Geometry cube bounds [{origin}, {size}] diverge from unit cube standard."
            )

        uv = root_cube.get("uv")
        if not isinstance(uv, dict):
            errors.append("Cube 'uv' mapping must be an object with per-face definitions.")
            return False, errors

        missing_faces = cls.REQUIRED_FACES - set(uv.keys())
        if missing_faces:
            errors.append(f"Cube UV definition missing required faces: {sorted(missing_faces)}.")

        return len(errors) == 0, errors

    @classmethod
    def validate_geometry(
        cls,
        geo_data: Dict[str, Any],
        expected_identifier: str = "",
    ) -> GeometryDefinition:
        """Validate that a geometry object satisfies Bedrock block outline standards.

        Args:
            geo_data: Parsed geometry JSON dictionary.
            expected_identifier: Optional expected geometry identifier string.

        Returns:
            GeometryDefinition dataclass with validation findings.
        """
        errors: List[str] = []
        if not isinstance(geo_data, dict):
            return GeometryDefinition(
                identifier=expected_identifier,
                is_valid=False,
                errors=["Geometry payload must be a JSON object."],
            )

        geo_list = geo_data.get("minecraft:geometry")
        if not isinstance(geo_list, list) or not geo_list:
            return GeometryDefinition(
                identifier=expected_identifier,
                is_valid=False,
                errors=["Missing or empty 'minecraft:geometry' array in payload."],
            )

        primary_geo = geo_list[0]
        desc = primary_geo.get("description", {})
        identifier = desc.get("identifier", "")

        if not identifier:
            errors.append("Geometry description missing required 'identifier'.")
        elif expected_identifier and identifier != expected_identifier:
            errors.append(
                f"Geometry identifier '{identifier}' does not match '{expected_identifier}'."
            )

        tex_dims = (desc.get("texture_width", 16), desc.get("texture_height", 16))
        bones = primary_geo.get("bones", [])
        if not isinstance(bones, list) or not bones:
            errors.append("Geometry definition missing required 'bones' list.")
            return GeometryDefinition(
                identifier=identifier,
                texture_size=tex_dims,
                is_valid=False,
                errors=errors,
            )

        _, cube_errors = cls._validate_cubes(bones[0].get("cubes", []))
        errors.extend(cube_errors)

        valid = len(errors) == 0
        return GeometryDefinition(
            identifier=identifier,
            texture_size=tex_dims,
            origin=list(cls.UNIT_ORIGIN),
            size=list(cls.UNIT_SIZE),
            bones=bones,
            is_valid=valid,
            errors=errors,
        )
