"""Validation engine for Bedrock humanoid entity geometry definitions and UV maps."""

from typing import Any, Optional
from packages.bedrock_uv_geometry.models import (
    ArmModelType,
    BedrockGeometry,
    ValidationReport,
    ValidationSeverity,
)


class BedrockUVValidator:
    """Comprehensive validator for humanoid geometry UV coordinates and schemas."""

    def __init__(self, target_version: str = "1.21.50") -> None:
        """Initialize validator with target Minecraft engine version context."""
        self.target_version = target_version

    def validate_file(
        self,
        file_path: str,
        expected_arm_type: Optional[ArmModelType] = None,
    ) -> ValidationReport:
        """Validate geometry file directly from filesystem path."""
        import json  # pylint: disable=import-outside-toplevel

        report = ValidationReport()
        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            geo = BedrockGeometry.from_dict(data)
            return self.validate_geometry(geo, expected_arm_type)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            report.add_issue("FILE_LOAD_ERROR", f"Failed to load file: {exc}")
            return report

    def validate_geometry(
        self,
        geometry: BedrockGeometry,
        expected_arm_type: Optional[ArmModelType] = None,
    ) -> ValidationReport:
        """Execute all validation rules against provided geometry model."""
        report = ValidationReport()

        self._validate_texture_dimensions(geometry, report)
        self._validate_bone_hierarchy(geometry, report)
        self._validate_limb_mirroring(geometry, report)
        self._validate_uv_coordinates(geometry, report)
        self._validate_uv_bounds(geometry, report)

        if expected_arm_type is not None:
            self._validate_arm_dimensions(geometry, expected_arm_type, report)

        return report

    def _validate_texture_dimensions(
        self,
        geometry: BedrockGeometry,
        report: ValidationReport,
    ) -> None:
        """Verify texture width and height conform to modern 64x64 specification."""
        desc = geometry.description
        if desc.texture_width == 64 and desc.texture_height == 32:
            report.add_issue(
                code="LEGACY_32X64_TEXTURE_DETECTED",
                message=(
                    "Legacy 64x32 texture resolution detected. "
                    "Bedrock 1.21.50+ requires 64x64 UV layout."
                ),
                severity=ValidationSeverity.ERROR,
            )
            return

        if desc.texture_width != 64 or desc.texture_height != 64:
            report.add_issue(
                code="INVALID_TEXTURE_DIMENSIONS",
                message=(
                    f"Invalid resolution {desc.texture_width}x{desc.texture_height}. "
                    "Expected 64x64."
                ),
                severity=ValidationSeverity.ERROR,
            )

    def _validate_bone_hierarchy(
        self,
        geometry: BedrockGeometry,
        report: ValidationReport,
    ) -> None:
        """Verify bone names and parent-child linkage relationships."""
        bone_names = {b.name for b in geometry.bones}

        required_bones = ["root", "body", "head", "rightArm", "leftArm", "rightLeg", "leftLeg"]
        for required in required_bones:
            if required not in bone_names:
                report.add_issue(
                    code="MISSING_HUMANOID_BONE",
                    message=f"Mandatory humanoid bone '{required}' is missing from skeleton.",
                    bone_name=required,
                    severity=ValidationSeverity.ERROR,
                )

        for bone in geometry.bones:
            if bone.parent and bone.parent not in bone_names:
                report.add_issue(
                    code="ORPHANED_BONE_PARENT",
                    message=f"Bone '{bone.name}' references missing parent '{bone.parent}'.",
                    bone_name=bone.name,
                    severity=ValidationSeverity.ERROR,
                )

    def _validate_limb_mirroring(
        self,
        geometry: BedrockGeometry,
        report: ValidationReport,
    ) -> None:
        """Detect legacy mirror flags on left limbs that trigger texture scrambling."""
        mirror_targets = {
            "leftArm": "MIRRORED_LEFT_ARM_DETECTED",
            "leftLeg": "MIRRORED_LEFT_LEG_DETECTED",
            "leftSleeve": "MIRRORED_LEFT_SLEEVE_DETECTED",
            "leftPants": "MIRRORED_LEFT_PANTS_DETECTED",
        }

        for bone_name, error_code in mirror_targets.items():
            bone = geometry.get_bone(bone_name)
            if not bone:
                continue

            if bone.mirror is True:
                report.add_issue(
                    code=error_code,
                    message=f"Bone '{bone_name}' specifies legacy bone-level mirror flag.",
                    bone_name=bone_name,
                    severity=ValidationSeverity.ERROR,
                )

            for idx, cube in enumerate(bone.cubes):
                if cube.mirror is True:
                    report.add_issue(
                        code=error_code,
                        message=f"Cube {idx} in bone '{bone_name}' specifies legacy mirror:true.",
                        bone_name=bone_name,
                        severity=ValidationSeverity.ERROR,
                    )

    def _validate_uv_coordinates(
        self,
        geometry: BedrockGeometry,
        report: ValidationReport,
    ) -> None:
        """Verify bones utilize modern unmirrored 64x64 independent UV coordinate sets."""
        left_arm = geometry.get_bone("leftArm")
        if left_arm and left_arm.cubes:
            first_cube = left_arm.cubes[0]
            if first_cube.is_box_uv:
                uv_u = float(first_cube.uv[0])  # type: ignore[index]
                uv_v = float(first_cube.uv[1])  # type: ignore[index]
                if (uv_u, uv_v) == (40.0, 16.0):
                    report.add_issue(
                        code="LEGACY_LEFT_ARM_UV_DETECTED",
                        message=(
                            "Bone 'leftArm' references rightArm UV [40, 16] "
                            "instead of [32, 48]."
                        ),
                        bone_name="leftArm",
                        severity=ValidationSeverity.ERROR,
                    )
                elif (uv_u, uv_v) != (32.0, 48.0):
                    report.add_issue(
                        code="NON_STANDARD_LEFT_ARM_UV",
                        message=(
                            f"Bone 'leftArm' UV ({uv_u}, {uv_v}) differs from "
                            "standard offset [32, 48]."
                        ),
                        bone_name="leftArm",
                        severity=ValidationSeverity.WARNING,
                    )

        left_leg = geometry.get_bone("leftLeg")
        if left_leg and left_leg.cubes:
            first_cube = left_leg.cubes[0]
            if first_cube.is_box_uv:
                uv_u = float(first_cube.uv[0])  # type: ignore[index]
                uv_v = float(first_cube.uv[1])  # type: ignore[index]
                if (uv_u, uv_v) == (0.0, 16.0):
                    report.add_issue(
                        code="LEGACY_LEFT_LEG_UV_DETECTED",
                        message=(
                            "Bone 'leftLeg' references rightLeg UV [0, 16] "
                            "instead of [16, 48]."
                        ),
                        bone_name="leftLeg",
                        severity=ValidationSeverity.ERROR,
                    )
                elif (uv_u, uv_v) != (16.0, 48.0):
                    report.add_issue(
                        code="NON_STANDARD_LEFT_LEG_UV",
                        message=(
                            f"Bone 'leftLeg' UV ({uv_u}, {uv_v}) differs from "
                            "standard offset [16, 48]."
                        ),
                        bone_name="leftLeg",
                        severity=ValidationSeverity.WARNING,
                    )

    def _validate_uv_bounds(
        self,
        geometry: BedrockGeometry,
        report: ValidationReport,
    ) -> None:
        """Ensure all cube UV bounding rectangles remain within texture surface boundaries."""
        tex_w = geometry.description.texture_width
        tex_h = geometry.description.texture_height

        for bone in geometry.bones:
            for idx, cube in enumerate(bone.cubes):
                if cube.is_box_uv:
                    u_origin = float(cube.uv[0])  # type: ignore[index]
                    v_origin = float(cube.uv[1])  # type: ignore[index]
                    size_x, size_y, size_z = cube.size

                    span_w = 2.0 * (size_z + size_x)
                    span_h = size_z + size_y

                    if u_origin < 0 or v_origin < 0:
                        report.add_issue(
                            code="UV_NEGATIVE_COORDINATES",
                            message=(
                                f"Cube {idx} in bone '{bone.name}' has negative UV "
                                f"offset ({u_origin}, {v_origin})."
                            ),
                            bone_name=bone.name,
                            severity=ValidationSeverity.ERROR,
                        )

                    if (u_origin + span_w) > tex_w or (v_origin + span_h) > tex_h:
                        report.add_issue(
                            code="UV_OUT_OF_BOUNDS",
                            message=(
                                f"Cube {idx} in bone '{bone.name}' UV bounds "
                                f"exceed texture dimensions {tex_w}x{tex_h}."
                            ),
                            bone_name=bone.name,
                            severity=ValidationSeverity.ERROR,
                        )
                elif isinstance(cube.uv, dict):
                    self._validate_per_face_uv_bounds(
                        bone.name,
                        cube.uv,
                        (tex_w, tex_h),
                        report,
                    )

    def _validate_per_face_uv_bounds(
        self,
        bone_name: str,
        face_dict: dict[str, Any],
        tex_dims: tuple[int, int],
        report: ValidationReport,
    ) -> None:
        """Ensure per-face UV coordinates remain within texture dimensions."""
        tex_w, tex_h = tex_dims
        for face_name, face_data in face_dict.items():
            if not isinstance(face_data, dict):
                continue
            uv = face_data.get("uv", [0.0, 0.0])
            uv_size = face_data.get("uv_size", [0.0, 0.0])

            u_start, v_start = float(uv[0]), float(uv[1])
            u_span, v_span = abs(float(uv_size[0])), abs(float(uv_size[1]))

            if (u_start + u_span) > tex_w or (v_start + v_span) > tex_h:
                report.add_issue(
                    code="PER_FACE_UV_OUT_OF_BOUNDS",
                    message=f"Per-face UV for '{face_name}' in '{bone_name}' exceeds bounds.",
                    bone_name=bone_name,
                    severity=ValidationSeverity.ERROR,
                )

    def _validate_arm_dimensions(
        self,
        geometry: BedrockGeometry,
        expected_type: ArmModelType,
        report: ValidationReport,
    ) -> None:
        """Validate arm bone thickness against expected player model archetype."""
        expected_width = 4.0 if expected_type == ArmModelType.CLASSIC else 3.0

        for arm_name in ["rightArm", "leftArm"]:
            bone = geometry.get_bone(arm_name)
            if not bone or not bone.cubes:
                continue

            cube = bone.cubes[0]
            actual_width = cube.size[0]

            if abs(actual_width - expected_width) > 0.01:
                report.add_issue(
                    code="ARM_DIMENSION_MISMATCH",
                    message=(
                        f"Bone '{arm_name}' cube width is {actual_width}, but expected "
                        f"{expected_width} for {expected_type.value} model."
                    ),
                    bone_name=arm_name,
                    severity=ValidationSeverity.ERROR,
                )
