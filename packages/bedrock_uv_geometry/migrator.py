"""Migration routines for converting legacy mirrored humanoid geometries to Bedrock 64x64."""

import copy
from typing import Optional
from packages.bedrock_uv_geometry.models import (
    ArmModelType,
    BedrockGeometry,
    Bone,
    GeometryDescription,
)


class BedrockUVMigrator:
    """Migrates legacy humanoid entity geometries to modern unmirrored 64x64 layout."""

    def migrate_to_classic(
        self,
        geometry: BedrockGeometry,
        new_identifier: Optional[str] = None,
    ) -> BedrockGeometry:
        """Migrate model specifically to classic 4-pixel arm humanoid layout."""
        return self.migrate_geometry(
            geometry=geometry,
            target_arm_type=ArmModelType.CLASSIC,
            new_identifier=new_identifier,
        )

    def migrate_to_slim(
        self,
        geometry: BedrockGeometry,
        new_identifier: Optional[str] = None,
    ) -> BedrockGeometry:
        """Migrate model specifically to slim 3-pixel arm humanoid layout."""
        return self.migrate_geometry(
            geometry=geometry,
            target_arm_type=ArmModelType.SLIM,
            new_identifier=new_identifier,
        )

    def migrate_geometry(
        self,
        geometry: BedrockGeometry,
        target_arm_type: Optional[ArmModelType] = None,
        new_identifier: Optional[str] = None,
    ) -> BedrockGeometry:
        """Upgrade geometry to modern 64x64 specification and resolve mirroring."""
        desc_data = geometry.description.to_dict()
        desc_data["texture_width"] = 64
        desc_data["texture_height"] = 64
        if new_identifier:
            desc_data["identifier"] = new_identifier

        migrated_description = GeometryDescription.from_dict(desc_data)
        migrated_bones: list[Bone] = []

        for bone in geometry.bones:
            new_bone = self._migrate_single_bone(bone, target_arm_type)
            migrated_bones.append(new_bone)

        return BedrockGeometry(
            description=migrated_description,
            bones=migrated_bones,
            format_version="1.12.0",
        )

    def _migrate_single_bone(
        self,
        bone: Bone,
        target_arm_type: Optional[ArmModelType] = None,
    ) -> Bone:
        """Process and remap bone properties and its contained cubes."""
        bone_copy = copy.deepcopy(bone)
        bone_copy.mirror = None

        if bone.name == "leftArm":
            self._migrate_left_arm(bone_copy, target_arm_type)
        elif bone.name == "leftLeg":
            self._migrate_left_leg(bone_copy)
        elif bone.name == "rightArm":
            self._migrate_right_arm(bone_copy, target_arm_type)
        elif bone.name == "leftSleeve":
            self._migrate_left_sleeve(bone_copy, target_arm_type)
        elif bone.name == "leftPants":
            self._migrate_left_pants(bone_copy)
        elif bone.name == "rightSleeve":
            self._migrate_right_sleeve(bone_copy, target_arm_type)

        return bone_copy

    def _migrate_left_arm(self, bone: Bone, target_arm_type: Optional[ArmModelType]) -> None:
        """Remap leftArm to discrete 64x64 UV offset [32, 48] and adjust slim/classic width."""
        arm_width = 4.0
        if target_arm_type == ArmModelType.SLIM:
            arm_width = 3.0
            bone.pivot = (5.0, 21.5, 0.0)
        elif target_arm_type == ArmModelType.CLASSIC:
            arm_width = 4.0
            bone.pivot = (5.0, 22.0, 0.0)

        for cube in bone.cubes:
            cube.mirror = False
            origin_x = 4.0
            cube.origin = (origin_x, cube.origin[1], cube.origin[2])
            cube.size = (arm_width, cube.size[1], cube.size[2])
            if cube.is_box_uv:
                cube.uv = (32.0, 48.0)

    def _migrate_left_leg(self, bone: Bone) -> None:
        """Remap leftLeg to discrete 64x64 UV offset [16, 48] and unmirror cubes."""
        for cube in bone.cubes:
            cube.mirror = False
            if cube.is_box_uv:
                cube.uv = (16.0, 48.0)

    def _migrate_right_arm(self, bone: Bone, target_arm_type: Optional[ArmModelType]) -> None:
        """Adjust rightArm dimensions and pivot for classic vs slim variant."""
        if target_arm_type is None:
            return

        arm_width = 4.0 if target_arm_type == ArmModelType.CLASSIC else 3.0
        pivot_y = 22.0 if target_arm_type == ArmModelType.CLASSIC else 21.5
        origin_x = -8.0 if target_arm_type == ArmModelType.CLASSIC else -7.0

        bone.pivot = (-5.0, pivot_y, 0.0)
        for cube in bone.cubes:
            cube.origin = (origin_x, cube.origin[1], cube.origin[2])
            cube.size = (arm_width, cube.size[1], cube.size[2])

    def _migrate_left_sleeve(self, bone: Bone, target_arm_type: Optional[ArmModelType]) -> None:
        """Remap left sleeve outer layer to [48, 48] unmirrored."""
        arm_width = 4.0 if target_arm_type != ArmModelType.SLIM else 3.0
        if target_arm_type == ArmModelType.SLIM:
            bone.pivot = (5.0, 21.5, 0.0)
        elif target_arm_type == ArmModelType.CLASSIC:
            bone.pivot = (5.0, 22.0, 0.0)

        for cube in bone.cubes:
            cube.mirror = False
            cube.origin = (4.0, cube.origin[1], cube.origin[2])
            cube.size = (arm_width, cube.size[1], cube.size[2])
            if cube.is_box_uv:
                cube.uv = (48.0, 48.0)

    def _migrate_left_pants(self, bone: Bone) -> None:
        """Remap left pants outer layer to [0, 48] unmirrored."""
        for cube in bone.cubes:
            cube.mirror = False
            if cube.is_box_uv:
                cube.uv = (0.0, 48.0)

    def _migrate_right_sleeve(self, bone: Bone, target_arm_type: Optional[ArmModelType]) -> None:
        """Adjust right sleeve outer layer dimensions."""
        if target_arm_type is None:
            return

        arm_width = 4.0 if target_arm_type == ArmModelType.CLASSIC else 3.0
        pivot_y = 22.0 if target_arm_type == ArmModelType.CLASSIC else 21.5
        origin_x = -8.0 if target_arm_type == ArmModelType.CLASSIC else -7.0

        bone.pivot = (-5.0, pivot_y, 0.0)
        for cube in bone.cubes:
            cube.origin = (origin_x, cube.origin[1], cube.origin[2])
            cube.size = (arm_width, cube.size[1], cube.size[2])
