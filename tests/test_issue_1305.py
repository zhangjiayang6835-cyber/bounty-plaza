"""Comprehensive test suite for Issue #1305: Hitbox Math and Continuous Collision Detection."""

import math
import pytest

from packages.hitbox_math.geometry import BoundingBox, Vector3
from packages.hitbox_math.swept_ccd import HitboxCcdEngine
from packages.hitbox_math.verifier import HitboxMathVerifier


class TestBedrockGeometry:
    """Validates Bedrock 3D coordinate system and bounding box math."""

    def test_vector_operations(self) -> None:
        """Tests vector addition, subtraction, scaling, dot and cross products."""
        vec_a = Vector3(1.0, 2.0, 3.0)
        vec_b = Vector3(4.0, 5.0, 6.0)

        sum_vec = vec_a.add(vec_b)
        assert (sum_vec.x, sum_vec.y, sum_vec.z) == (5.0, 7.0, 9.0)

        sub_vec = vec_b.subtract(vec_a)
        assert (sub_vec.x, sub_vec.y, sub_vec.z) == (3.0, 3.0, 3.0)

        scale_vec = vec_a.scale(2.0)
        assert (scale_vec.x, scale_vec.y, scale_vec.z) == (2.0, 4.0, 6.0)

        assert vec_a.dot(vec_b) == 32.0

        cross = Vector3(1.0, 0.0, 0.0).cross(Vector3(0.0, 1.0, 0.0))
        assert (cross.x, cross.y, cross.z) == (0.0, 0.0, 1.0)

        assert pytest.approx(Vector3(3.0, 4.0, 0.0).magnitude(), 1e-6) == 5.0
        norm = Vector3(0.0, 10.0, 0.0).normalize()
        assert (norm.x, norm.y, norm.z) == (0.0, 1.0, 0.0)

    def test_bedrock_cardinal_coordinates(self) -> None:
        """Tests Minecraft Bedrock cardinal directions (+X East, +Y Up, +Z South)."""
        box = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(1.0, 1.0, 1.0))
        faces = box.get_faces()
        face_map = {f.name: (f.normal.x, f.normal.y, f.normal.z) for f in faces}

        assert face_map["East"] == (1.0, 0.0, 0.0)
        assert face_map["West"] == (-1.0, 0.0, 0.0)
        assert face_map["Up"] == (0.0, 1.0, 0.0)
        assert face_map["Down"] == (0.0, -1.0, 0.0)
        assert face_map["South"] == (0.0, 0.0, 1.0)
        assert face_map["North"] == (0.0, 0.0, -1.0)

    def test_derive_eight_vertices(self) -> None:
        """Tests derivation of eight bounding box corner vertices."""
        box = BoundingBox(Vector3(10.0, 20.0, 30.0), Vector3(1.0, 2.0, 3.0))
        vertices = box.derive_vertices()
        assert len(vertices) == 8

        min_p = box.min_point
        max_p = box.max_point
        assert (min_p.x, min_p.y, min_p.z) == (9.0, 18.0, 27.0)
        assert (max_p.x, max_p.y, max_p.z) == (11.0, 22.0, 33.0)

        coords = {(v.x, v.y, v.z) for v in vertices}
        assert (9.0, 18.0, 27.0) in coords
        assert (11.0, 22.0, 33.0) in coords
        assert len(coords) == 8

    def test_bounding_box_expansion(self) -> None:
        """Tests Minkowski broadphase expansion over displacement vector."""
        box = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(1.0, 1.0, 1.0))
        expanded = box.expand(Vector3(5.0, 0.0, 0.0))

        assert expanded.min_point.x == -1.0
        assert expanded.max_point.x == 6.0
        assert expanded.center.x == 2.5
        assert expanded.extent.x == 3.5


class TestSweptCollisionDetection:
    """Validates Swept Continuous Collision Detection engine."""

    def test_swept_collision_x_axis(self) -> None:
        """Tests continuous swept collision along positive X axis."""
        moving = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(1.0, 1.0, 1.0))
        obstacle = BoundingBox(Vector3(5.0, 0.0, 0.0), Vector3(1.0, 1.0, 1.0))
        velocity = Vector3(10.0, 0.0, 0.0)

        hit = HitboxCcdEngine.test_swept_aabb(moving, velocity, obstacle)
        assert hit.has_collision
        assert pytest.approx(hit.time_of_impact, 1e-5) == 0.3
        assert (hit.normal.x, hit.normal.y, hit.normal.z) == (-1.0, 0.0, 0.0)
        assert hit.cardinal_direction == "West"

    def test_swept_collision_miss(self) -> None:
        """Tests non-colliding swept trajectories."""
        moving = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(1.0, 1.0, 1.0))
        obstacle = BoundingBox(Vector3(5.0, 5.0, 0.0), Vector3(1.0, 1.0, 1.0))
        velocity = Vector3(10.0, 0.0, 0.0)

        hit = HitboxCcdEngine.test_swept_aabb(moving, velocity, obstacle)
        assert not hit.has_collision

    def test_dynamic_vs_dynamic(self) -> None:
        """Tests continuous collision between two moving entities."""
        box_a = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(1.0, 1.0, 1.0))
        vel_a = Vector3(6.0, 0.0, 0.0)
        box_b = BoundingBox(Vector3(10.0, 0.0, 0.0), Vector3(1.0, 1.0, 1.0))
        vel_b = Vector3(-4.0, 0.0, 0.0)

        hit = HitboxCcdEngine.test_dynamic_vs_dynamic(box_a, vel_a, box_b, vel_b)
        assert hit.has_collision
        assert pytest.approx(hit.time_of_impact, 1e-5) == 0.8


class TestKinematicTunnelingAndTick4192:
    """Validates tunneling prevention and tick 4192 raycast miss resolution."""

    def test_high_velocity_tunneling_prevention(self) -> None:
        """Tests prevention of tunneling at velocities greater than 1.5 blocks/tick."""
        moving = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(0.5, 1.0, 0.5))
        wall = BoundingBox(Vector3(2.0, 0.0, 0.0), Vector3(0.5, 4.0, 4.0))
        velocity = Vector3(6.0, 0.0, 0.0)

        res = HitboxCcdEngine.resolve_kinematic_step(moving, velocity, [wall])
        assert res.tunneling_prevented
        assert len(res.collisions) > 0
        assert res.final_position.x < wall.min_point.x

    def test_tick_4192_raycast_miss_resolution(self) -> None:
        """Specifically tests resolution of tick 4192 raycast miss log warning."""
        res = HitboxCcdEngine.validate_tick_4192_raycast()
        assert res.hit
        assert res.warning_miss_resolved
        assert res.tick == 4192
        assert res.sub_tick_fraction > 0.0
        assert res.distance < math.inf

    def test_multi_obstacle_sliding(self) -> None:
        """Tests sliding deflection along multiple collision planes."""
        moving = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(0.5, 0.5, 0.5))
        obs_a = BoundingBox(Vector3(2.0, 0.0, 0.0), Vector3(0.5, 2.0, 2.0))
        obs_b = BoundingBox(Vector3(2.0, 2.0, 0.0), Vector3(2.0, 0.5, 2.0))
        velocity = Vector3(4.0, 1.0, 0.0)

        res = HitboxCcdEngine.resolve_kinematic_step(moving, velocity, [obs_a, obs_b])
        assert res.final_position.x < obs_a.min_point.x

    def test_formal_verifier_suite(self) -> None:
        """Executes formal invariant verifier and verifies all checks pass."""
        report = HitboxMathVerifier.run_all_checks()
        assert report.all_passed
        assert report.checks_run == 7
