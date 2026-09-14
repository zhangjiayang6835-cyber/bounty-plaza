"""Collision dropout guard and continuous collision detection for ascending contraptions."""

from __future__ import annotations

from packages.kinematics_solver.models import (
    Vector3D,
    ColliderBox,
    CollisionResult,
    KinematicState,
)


class CollisionDropoutGuard:
    """Continuous collision verifier preventing player void dropout on moving assemblies."""

    def __init__(
        self,
        player_width: float = 0.6,
        player_height: float = 1.8,
        shulker_width: float = 1.0,
        shulker_height: float = 1.0,
    ) -> None:
        """Initialize dimensions for player and shulker composite colliders.

        :param player_width: Bounding box horizontal width of player entity.
        :param player_height: Bounding box vertical height of player entity.
        :param shulker_width: Shulker assembly horizontal dimension.
        :param shulker_height: Shulker assembly vertical dimension.
        """
        self.player_half_w = player_width / 2.0
        self.player_height = player_height
        self.shulker_half_w = shulker_width / 2.0
        self.shulker_height = shulker_height

    def make_player_box(self, feet_pos: Vector3D) -> ColliderBox:
        """Construct player AABB given base feet coordinates.

        :param feet_pos: Spatial location of player feet center.
        :return: ColliderBox for player.
        """
        return ColliderBox(
            min_point=Vector3D(
                feet_pos.x - self.player_half_w,
                feet_pos.y,
                feet_pos.z - self.player_half_w,
            ),
            max_point=Vector3D(
                feet_pos.x + self.player_half_w,
                feet_pos.y + self.player_height,
                feet_pos.z + self.player_half_w,
            ),
        )

    def make_shulker_box(self, base_pos: Vector3D) -> ColliderBox:
        """Construct shulker composite AABB given bottom center position.

        :param base_pos: Spatial location of shulker base center.
        :return: ColliderBox for shulker.
        """
        return ColliderBox(
            min_point=Vector3D(
                base_pos.x - self.shulker_half_w,
                base_pos.y,
                base_pos.z - self.shulker_half_w,
            ),
            max_point=Vector3D(
                base_pos.x + self.shulker_half_w,
                base_pos.y + self.shulker_height,
                base_pos.z + self.shulker_half_w,
            ),
        )

    def evaluate_contact(
        self,
        player_feet: Vector3D,
        shulker_base: Vector3D,
        vertical_tolerance: float = 0.05,
    ) -> CollisionResult:
        """Evaluate physical contact and support between player and shulker top face.

        :param player_feet: Position of player base.
        :param shulker_base: Position of shulker base.
        :param vertical_tolerance: Maximum threshold defining resting contact.
        :return: CollisionResult reporting contact and support status.
        """
        p_box = self.make_player_box(player_feet)
        s_box = self.make_shulker_box(shulker_base)

        top_face = s_box.top_face_y()
        separation = player_feet.y - top_face

        horizontal_overlap = (
            p_box.min_point.x <= s_box.max_point.x
            and p_box.max_point.x >= s_box.min_point.x
            and p_box.min_point.z <= s_box.max_point.z
            and p_box.max_point.z >= s_box.min_point.z
        )

        is_supported = horizontal_overlap and (-0.01 <= separation <= vertical_tolerance)
        has_collision = horizontal_overlap and p_box.intersects(s_box)

        normal = Vector3D(0.0, 1.0, 0.0) if is_supported else Vector3D(0.0, 0.0, 0.0)

        return CollisionResult(
            has_collision=has_collision or is_supported,
            separation_distance=separation,
            normal=normal,
            is_supported=is_supported,
        )

    def resolve_support(
        self,
        player_feet: Vector3D,
        shulker_base: Vector3D,
    ) -> tuple[Vector3D, bool]:
        """Enforce non-penetrating kinematic support constraint on player.

        :param player_feet: Intended player feet coordinate.
        :param shulker_base: Target shulker base coordinate.
        :return: Tuple of resolved player position vector and support boolean.
        """
        s_box = self.make_shulker_box(shulker_base)
        top_y = s_box.top_face_y()

        p_box = self.make_player_box(player_feet)
        horizontal_overlap = (
            p_box.min_point.x <= s_box.max_point.x
            and p_box.max_point.x >= s_box.min_point.x
            and p_box.min_point.z <= s_box.max_point.z
            and p_box.max_point.z >= s_box.min_point.z
        )

        if horizontal_overlap and player_feet.y <= top_y + 0.05:
            resolved_pos = Vector3D(player_feet.x, top_y, player_feet.z)
            return resolved_pos, True

        return player_feet, False

    def simulate_ascent(
        self,
        contraption_trajectory: list[KinematicState],
        initial_player_feet: Vector3D,
    ) -> dict[str, float | int | bool]:
        """Simulate vertical contraption ascent verifying zero collision dropouts.

        :param contraption_trajectory: Chronological kinematic states of collider.
        :param initial_player_feet: Initial resting player position.
        :return: Telemetry dictionary summarizing collision metrics.
        """
        dropouts = 0
        total_steps = len(contraption_trajectory)
        current_player = initial_player_feet
        max_separation = 0.0

        for i, state in enumerate(contraption_trajectory):
            if i > 0:
                prev_state = contraption_trajectory[i - 1]
                delta_disp = state.position - prev_state.position
                current_player = current_player + delta_disp

            current_player, was_supported = self.resolve_support(current_player, state.position)
            contact = self.evaluate_contact(current_player, state.position)

            if not (was_supported and contact.is_supported):
                dropouts += 1

            max_separation = max(max_separation, abs(contact.separation_distance))

        dropout_rate = (dropouts / total_steps) if total_steps > 0 else 0.0

        return {
            "total_steps": total_steps,
            "dropouts": dropouts,
            "dropout_rate": dropout_rate,
            "max_separation": max_separation,
            "zero_dropout_verified": dropouts == 0,
        }
