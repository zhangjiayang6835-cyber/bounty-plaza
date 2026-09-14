"""Validator and analyzer for Bedrock humanoid client entities and geometries."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .models import (
    BoneDefinition,
    ClientEntityDefinition,
    ValidationReport,
)


class HumanoidEntityValidator:
    """Validates Bedrock client entity definitions for humanoid compliance."""

    ALLOWED_MATERIALS = {"entity_alphatest", "entity_alphablend", "default"}
    LEGACY_GEOMETRIES = {
        "geometry.zombie",
        "geometry.zombie.v1.8",
        "geometry.humanoid.v1.8",
    }
    MODERN_HUMANOID_GEOMETRIES = {
        "geometry.humanoid.custom",
        "geometry.humanoid.customSlim",
    }

    def validate_entity_file(
        self, file_path: Union[str, Path]
    ) -> ValidationReport:
        """Read and validate a client entity JSON file from filesystem."""
        path = Path(file_path)
        if not path.is_file():
            report = ValidationReport(is_valid=False)
            report.add_issue(
                "FATAL",
                "FILE_NOT_FOUND",
                f"Client entity file not found: {path}",
                str(path),
            )
            return report

        try:
            with open(path, "r", encoding="utf-8") as file_handle:
                data = json.load(file_handle)
        except json.JSONDecodeError as exc:
            report = ValidationReport(is_valid=False)
            report.add_issue(
                "FATAL",
                "JSON_PARSE_ERROR",
                f"Failed to parse JSON content: {exc}",
                str(path),
            )
            return report

        return self.validate_entity_dict(data, source_path=str(path))

    def validate_entity_dict(
        self, data: Dict[str, Any], source_path: str = ""
    ) -> ValidationReport:
        """Validate an in-memory client entity dictionary."""
        report = ValidationReport(is_valid=True)

        if "format_version" not in data:
            report.add_issue(
                "ERROR",
                "MISSING_FORMAT_VERSION",
                "Root definition missing 'format_version' key.",
                source_path,
            )

        client_entity = data.get("minecraft:client_entity")
        if not isinstance(client_entity, dict):
            report.add_issue(
                "FATAL",
                "MISSING_CLIENT_ENTITY",
                "Root definition missing 'minecraft:client_entity' object.",
                source_path,
            )
            return report

        description = client_entity.get("description")
        if not isinstance(description, dict):
            report.add_issue(
                "FATAL",
                "MISSING_DESCRIPTION",
                "Client entity definition missing 'description' object.",
                source_path,
            )
            return report

        entity_def = ClientEntityDefinition.from_dict(data)
        desc = entity_def.description

        if not desc.identifier:
            report.add_issue(
                "ERROR",
                "MISSING_IDENTIFIER",
                "Entity description identifier cannot be empty.",
                source_path,
            )

        default_geo = desc.geometry.get("default", "")
        if not default_geo:
            report.add_issue(
                "ERROR",
                "MISSING_DEFAULT_GEOMETRY",
                "Entity description missing default geometry mapping.",
                source_path,
            )
        elif default_geo in self.LEGACY_GEOMETRIES:
            report.add_issue(
                "ERROR",
                "LEGACY_GEOMETRY_DETECTED",
                f"Legacy geometry '{default_geo}' enforces 64x32 UV mirroring, "
                "scrambling asymmetric arm/leg textures and omitting outer skin layers.",
                source_path,
            )
        elif default_geo in self.MODERN_HUMANOID_GEOMETRIES:
            report.details["geometry_model"] = default_geo
        else:
            report.add_issue(
                "WARNING",
                "UNVERIFIED_GEOMETRY",
                f"Non-standard geometry '{default_geo}' detected.",
                source_path,
            )

        render_controllers = desc.render_controllers
        if not render_controllers:
            report.add_issue(
                "ERROR",
                "MISSING_RENDER_CONTROLLERS",
                "Entity description must specify at least one render controller.",
                source_path,
            )
        elif "controller.render.zombie" in render_controllers:
            report.add_issue(
                "ERROR",
                "INCOMPATIBLE_RENDER_CONTROLLER",
                "Controller 'controller.render.zombie' binds rigid zombie poses and "
                "fails to render dual-layer player outer skin geometry.",
                source_path,
            )

        mat_default = desc.materials.get("default", "")
        if mat_default and mat_default not in self.ALLOWED_MATERIALS:
            report.add_issue(
                "WARNING",
                "SUBOPTIMAL_MATERIAL",
                f"Material '{mat_default}' may cause opaque black outer layers; "
                "prefer 'entity_alphatest'.",
                source_path,
            )

        return report


class GeometryModelAnalyzer:
    """Analyzes Bedrock geometry files to verify UV mappings and outer layers."""

    REQUIRED_OUTER_BONES = {
        "hat": "head",
        "jacket": "body",
        "rightSleeve": "rightArm",
        "leftSleeve": "leftArm",
        "rightPants": "rightLeg",
        "leftPants": "leftLeg",
    }

    def analyze_geometry_file(
        self, file_path: Union[str, Path]
    ) -> ValidationReport:
        """Read and analyze a geometry model JSON file from filesystem."""
        path = Path(file_path)
        if not path.is_file():
            report = ValidationReport(is_valid=False)
            report.add_issue(
                "FATAL",
                "FILE_NOT_FOUND",
                f"Geometry file not found: {path}",
                str(path),
            )
            return report

        try:
            with open(path, "r", encoding="utf-8") as file_handle:
                data = json.load(file_handle)
        except json.JSONDecodeError as exc:
            report = ValidationReport(is_valid=False)
            report.add_issue(
                "FATAL",
                "JSON_PARSE_ERROR",
                f"Failed to parse geometry JSON: {exc}",
                str(path),
            )
            return report

        return self.analyze_geometry_dict(data, source_path=str(path))

    def analyze_geometry_dict(
        self, data: Dict[str, Any], source_path: str = ""
    ) -> ValidationReport:
        """Analyze geometry structure, asymmetry, and dual-layer components."""
        report = ValidationReport(is_valid=True)
        geo_item = self._extract_geometry_item(data)
        if not geo_item:
            report.add_issue(
                "FATAL",
                "MISSING_GEOMETRY_NODE",
                "Could not locate geometry specification node in model definition.",
                source_path,
            )
            return report

        description = geo_item.get("description", {})
        tex_w = description.get("texture_width", 64)
        tex_h = description.get("texture_height", 64)
        if tex_w != 64 or tex_h != 64:
            report.add_issue(
                "ERROR",
                "INVALID_TEXTURE_DIMENSIONS",
                f"Expected 64x64 texture bounds, found {tex_w}x{tex_h}.",
                source_path,
            )

        bones_dict = self._index_bones(geo_item.get("bones", []))
        self._verify_asymmetry(bones_dict, report, source_path)
        self._verify_outer_layers(bones_dict, report, source_path)

        return report

    def _extract_geometry_item(
        self, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Extract the target geometry object across Bedrock format variants."""
        if "minecraft:geometry" in data and isinstance(
            data["minecraft:geometry"], list
        ):
            if len(data["minecraft:geometry"]) > 0:
                return data["minecraft:geometry"][0]
        for key, value in data.items():
            if key.startswith("geometry.") and isinstance(value, dict):
                return value
        return None

    def _index_bones(
        self, raw_bones: List[Dict[str, Any]]
    ) -> Dict[str, BoneDefinition]:
        """Index raw bone items into a dictionary of BoneDefinition objects."""
        indexed: Dict[str, BoneDefinition] = {}
        for bone_data in raw_bones:
            bone = BoneDefinition.from_dict(bone_data)
            indexed[bone.name] = bone
        return indexed

    def _verify_asymmetry(
        self,
        bones: Dict[str, BoneDefinition],
        report: ValidationReport,
        source_path: str,
    ) -> None:
        """Verify distinct asymmetric UV mapping for left and right limbs."""
        has_right_arm = "rightArm" in bones and len(bones["rightArm"].cubes) > 0
        has_left_arm = "leftArm" in bones and len(bones["leftArm"].cubes) > 0
        has_right_leg = "rightLeg" in bones and len(bones["rightLeg"].cubes) > 0
        has_left_leg = "leftLeg" in bones and len(bones["leftLeg"].cubes) > 0

        if not (has_right_arm and has_left_arm and has_right_leg and has_left_leg):
            report.add_issue(
                "ERROR",
                "MISSING_LIMB_BONES",
                "Geometry missing one or more core limb bones (arms or legs).",
                source_path,
            )
            return

        right_arm_uv = bones["rightArm"].cubes[0].uv
        left_arm_uv = bones["leftArm"].cubes[0].uv
        left_arm_mirror = bones["leftArm"].mirror or bones["leftArm"].cubes[0].mirror

        if right_arm_uv == left_arm_uv:
            report.add_issue(
                "ERROR",
                "MIRRORED_ARM_UV",
                f"Left arm shares UV coordinates {left_arm_uv} with right arm.",
                source_path,
            )
        if left_arm_mirror:
            report.add_issue(
                "ERROR",
                "MIRRORED_ARM_FLAG",
                "Left arm has mirror flag enabled, causing texture inversion.",
                source_path,
            )

        right_leg_uv = bones["rightLeg"].cubes[0].uv
        left_leg_uv = bones["leftLeg"].cubes[0].uv
        left_leg_mirror = bones["leftLeg"].mirror or bones["leftLeg"].cubes[0].mirror

        if right_leg_uv == left_leg_uv:
            report.add_issue(
                "ERROR",
                "MIRRORED_LEG_UV",
                f"Left leg shares UV coordinates {left_leg_uv} with right leg.",
                source_path,
            )
        if left_leg_mirror:
            report.add_issue(
                "ERROR",
                "MIRRORED_LEG_FLAG",
                "Left leg has mirror flag enabled, causing texture inversion.",
                source_path,
            )

        if not (
            right_arm_uv == left_arm_uv
            or left_arm_mirror
            or right_leg_uv == left_leg_uv
            or left_leg_mirror
        ):
            report.asymmetric_limbs_supported = True

    def _verify_outer_layers(
        self,
        bones: Dict[str, BoneDefinition],
        report: ValidationReport,
        source_path: str,
    ) -> None:
        """Verify presence and inflation of dual-layer outer skin meshes."""
        missing_outer = []
        uninflated_outer = []

        for outer_name in self.REQUIRED_OUTER_BONES:
            if outer_name not in bones:
                missing_outer.append(outer_name)
                continue
            outer_bone = bones[outer_name]
            if not outer_bone.cubes:
                missing_outer.append(outer_name)
                continue
            cube = outer_bone.cubes[0]
            if cube.inflate <= 0.0:
                uninflated_outer.append(outer_name)

        if missing_outer:
            report.add_issue(
                "ERROR",
                "MISSING_OUTER_LAYERS",
                f"Geometry is missing outer layer bones: {missing_outer}",
                source_path,
            )
        if uninflated_outer:
            report.add_issue(
                "WARNING",
                "UNINFLATED_OUTER_LAYERS",
                f"Outer layer bones lack cube inflation: {uninflated_outer}",
                source_path,
            )

        if not missing_outer and not uninflated_outer:
            report.dual_layer_supported = True
