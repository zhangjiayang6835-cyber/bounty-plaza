"""Programmatic generator for modern Bedrock humanoid NPC geometries."""

from packages.bedrock_uv_geometry.models import (
    ArmModelType,
    BedrockGeometry,
    Bone,
    Cube,
    GeometryDescription,
)


class BedrockHumanoidGenerator:
    """Generates specification-compliant 64x64 humanoid geometries."""

    @classmethod
    def generate_classic(
        cls,
        identifier: str = "geometry.custom_npc",
        include_outer_layers: bool = True,
    ) -> BedrockGeometry:
        """Construct classic humanoid geometry with 4-pixel thick arms."""
        return cls.generate_humanoid(
            identifier=identifier,
            arm_type=ArmModelType.CLASSIC,
            include_outer_layers=include_outer_layers,
        )

    @classmethod
    def generate_slim(
        cls,
        identifier: str = "geometry.custom_npc.slim",
        include_outer_layers: bool = True,
    ) -> BedrockGeometry:
        """Construct slim humanoid geometry with 3-pixel thick arms."""
        return cls.generate_humanoid(
            identifier=identifier,
            arm_type=ArmModelType.SLIM,
            include_outer_layers=include_outer_layers,
        )

    @staticmethod
    def generate_humanoid(
        identifier: str = "geometry.custom_npc",
        arm_type: ArmModelType = ArmModelType.CLASSIC,
        include_outer_layers: bool = True,
    ) -> BedrockGeometry:
        """Construct complete canonical humanoid geometry with discrete limb UV mappings."""
        description = GeometryDescription(
            identifier=identifier,
            texture_width=64,
            texture_height=64,
            visible_bounds_width=1.5,
            visible_bounds_height=2.0,
            visible_bounds_offset=(0.0, 1.0, 0.0),
        )

        arm_width = 4.0 if arm_type == ArmModelType.CLASSIC else 3.0
        arm_pivot_y = 22.0 if arm_type == ArmModelType.CLASSIC else 21.5
        right_arm_origin_x = -8.0 if arm_type == ArmModelType.CLASSIC else -7.0

        bones: list[Bone] = [
            Bone(name="root", pivot=(0.0, 0.0, 0.0)),
            Bone(name="waist", parent="root", pivot=(0.0, 12.0, 0.0)),
            Bone(
                name="body",
                parent="waist",
                pivot=(0.0, 24.0, 0.0),
                cubes=[
                    Cube(
                        origin=(-4.0, 12.0, -2.0),
                        size=(8.0, 12.0, 4.0),
                        uv=(16.0, 16.0),
                    )
                ],
            ),
            Bone(
                name="head",
                parent="body",
                pivot=(0.0, 24.0, 0.0),
                cubes=[
                    Cube(
                        origin=(-4.0, 24.0, -4.0),
                        size=(8.0, 8.0, 8.0),
                        uv=(0.0, 0.0),
                    )
                ],
            ),
            Bone(
                name="rightArm",
                parent="body",
                pivot=(-5.0, arm_pivot_y, 0.0),
                cubes=[
                    Cube(
                        origin=(right_arm_origin_x, 12.0, -2.0),
                        size=(arm_width, 12.0, 4.0),
                        uv=(40.0, 16.0),
                    )
                ],
            ),
            Bone(
                name="leftArm",
                parent="body",
                pivot=(5.0, arm_pivot_y, 0.0),
                cubes=[
                    Cube(
                        origin=(4.0, 12.0, -2.0),
                        size=(arm_width, 12.0, 4.0),
                        uv=(32.0, 48.0),
                        mirror=False,
                    )
                ],
            ),
            Bone(
                name="rightLeg",
                parent="root",
                pivot=(-1.9, 12.0, 0.0),
                cubes=[
                    Cube(
                        origin=(-3.9, 0.0, -2.0),
                        size=(4.0, 12.0, 4.0),
                        uv=(0.0, 16.0),
                    )
                ],
            ),
            Bone(
                name="leftLeg",
                parent="root",
                pivot=(1.9, 12.0, 0.0),
                cubes=[
                    Cube(
                        origin=(-0.1, 0.0, -2.0),
                        size=(4.0, 12.0, 4.0),
                        uv=(16.0, 48.0),
                        mirror=False,
                    )
                ],
            ),
        ]

        if include_outer_layers:
            outer_bones = [
                Bone(
                    name="hat",
                    parent="head",
                    pivot=(0.0, 24.0, 0.0),
                    cubes=[
                        Cube(
                            origin=(-4.0, 24.0, -4.0),
                            size=(8.0, 8.0, 8.0),
                            uv=(32.0, 0.0),
                            inflate=0.5,
                        )
                    ],
                ),
                Bone(
                    name="jacket",
                    parent="body",
                    pivot=(0.0, 24.0, 0.0),
                    cubes=[
                        Cube(
                            origin=(-4.0, 12.0, -2.0),
                            size=(8.0, 12.0, 4.0),
                            uv=(16.0, 32.0),
                            inflate=0.25,
                        )
                    ],
                ),
                Bone(
                    name="rightSleeve",
                    parent="rightArm",
                    pivot=(-5.0, arm_pivot_y, 0.0),
                    cubes=[
                        Cube(
                            origin=(right_arm_origin_x, 12.0, -2.0),
                            size=(arm_width, 12.0, 4.0),
                            uv=(40.0, 32.0),
                            inflate=0.25,
                        )
                    ],
                ),
                Bone(
                    name="leftSleeve",
                    parent="leftArm",
                    pivot=(5.0, arm_pivot_y, 0.0),
                    cubes=[
                        Cube(
                            origin=(4.0, 12.0, -2.0),
                            size=(arm_width, 12.0, 4.0),
                            uv=(48.0, 48.0),
                            inflate=0.25,
                            mirror=False,
                        )
                    ],
                ),
                Bone(
                    name="rightPants",
                    parent="rightLeg",
                    pivot=(-1.9, 12.0, 0.0),
                    cubes=[
                        Cube(
                            origin=(-3.9, 0.0, -2.0),
                            size=(4.0, 12.0, 4.0),
                            uv=(0.0, 32.0),
                            inflate=0.25,
                        )
                    ],
                ),
                Bone(
                    name="leftPants",
                    parent="leftLeg",
                    pivot=(1.9, 12.0, 0.0),
                    cubes=[
                        Cube(
                            origin=(-0.1, 0.0, -2.0),
                            size=(4.0, 12.0, 4.0),
                            uv=(0.0, 48.0),
                            inflate=0.25,
                            mirror=False,
                        )
                    ],
                ),
            ]
            bones.extend(outer_bones)

        return BedrockGeometry(description=description, bones=bones, format_version="1.12.0")
