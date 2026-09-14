"""Unit test suite for Issue #1334 Bedrock Swept AABB Continuous Collision Detection.

Validates:
1. Bedrock coordinate alignment (+X East, -X West, +Y Up, -Y Down, +Z South, -Z North).
2. 8-vertex bounding box corner derivation.
3. Swept AABB Time of Impact and collision normal calculation.
4. Prevention of projectile/entity tunneling (> 1.5 blocks/tick).
5. Sub-tick raycast synchronization eliminating tick 5812 dropouts.
6. Dynamic vs dynamic relative velocity collision.
7. Multi-obstacle sliding deflection.
8. Full invariant verifier execution.
"""

from packages.kinematic_ccd.geometry import BoundingBox, Vector3
from packages.kinematic_ccd.swept_ccd import Ray, SweptAABBEngine
from packages.kinematic_ccd.verifier import KinematicCcdVerifier


def test_bedrock_coordinate_alignment() -> None:
    """Verifies that cardinal faces match Bedrock coordinate space."""
    box = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(1.0, 1.0, 1.0))
    faces = box.get_faces()
    assert len(faces) == 6

    face_dict = {f.name: f.normal for f in faces}
    assert face_dict["East"] == Vector3(1.0, 0.0, 0.0)
    assert face_dict["West"] == Vector3(-1.0, 0.0, 0.0)
    assert face_dict["Up"] == Vector3(0.0, 1.0, 0.0)
    assert face_dict["Down"] == Vector3(0.0, -1.0, 0.0)
    assert face_dict["South"] == Vector3(0.0, 0.0, 1.0)
    assert face_dict["North"] == Vector3(0.0, 0.0, -1.0)


def test_eight_vertex_derivation() -> None:
    """Verifies that all 8 spatial bounding vertices are derived correctly."""
    box = BoundingBox(Vector3(10.0, 20.0, 30.0), Vector3(2.0, 4.0, 6.0))
    vertices = box.derive_vertices()
    assert len(vertices) == 8

    assert vertices[0] == Vector3(8.0, 16.0, 24.0)
    assert vertices[1] == Vector3(12.0, 16.0, 24.0)
    assert vertices[2] == Vector3(8.0, 24.0, 24.0)
    assert vertices[3] == Vector3(12.0, 24.0, 24.0)
    assert vertices[4] == Vector3(8.0, 16.0, 36.0)
    assert vertices[5] == Vector3(12.0, 16.0, 36.0)
    assert vertices[6] == Vector3(8.0, 24.0, 36.0)
    assert vertices[7] == Vector3(12.0, 24.0, 36.0)


def test_swept_aabb_toi_and_normal() -> None:
    """Verifies exact swept AABB time of impact and collision normal."""
    moving = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(1.0, 1.0, 1.0))
    obstacle = BoundingBox(Vector3(5.0, 0.0, 0.0), Vector3(1.0, 1.0, 1.0))
    velocity = Vector3(10.0, 0.0, 0.0)

    hit = SweptAABBEngine.test_swept_aabb(moving, velocity, obstacle)
    assert hit.has_collision
    assert abs(hit.time_of_impact - 0.3) < 1e-5
    assert hit.normal == Vector3(-1.0, 0.0, 0.0)
    assert hit.cardinal_direction == "West"


def test_no_collision_when_disjoint() -> None:
    """Verifies no collision occurs when trajectories do not intersect."""
    moving = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(1.0, 1.0, 1.0))
    obstacle = BoundingBox(Vector3(5.0, 5.0, 5.0), Vector3(1.0, 1.0, 1.0))
    velocity = Vector3(10.0, 0.0, 0.0)

    hit = SweptAABBEngine.test_swept_aabb(moving, velocity, obstacle)
    assert not hit.has_collision
    assert hit.time_of_impact == 1.0


def test_high_velocity_tunneling_prevention() -> None:
    """Verifies that velocities exceeding 1.5 blocks/tick do not tunnel."""
    moving = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(1.0, 1.0, 1.0))
    wall = BoundingBox(Vector3(2.0, 0.0, 0.0), Vector3(0.5, 5.0, 5.0))
    velocity = Vector3(5.0, 0.0, 0.0)

    res = SweptAABBEngine.resolve_kinematic_step(moving, velocity, [wall])
    assert res.tunneling_prevented
    assert res.final_position.x <= wall.min_point.x


def test_sub_tick_raycast_synchronization() -> None:
    """Verifies that sub-tick raycast hits interpolated volume without dropout."""
    entity = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(1.0, 2.0, 1.0))
    velocity = Vector3(10.0, 0.0, 0.0)
    ray = Ray(
        origin=Vector3(5.0, 0.0, -10.0),
        direction=Vector3(0.0, 0.0, 1.0),
        max_distance=20.0,
    )

    res = SweptAABBEngine.synchronize_sub_tick_raycast(
        entity,
        velocity,
        ray,
        sub_tick_delta=0.5,
    )
    assert res.hit
    assert not res.warning_dropped


def test_multi_obstacle_sliding_resolution() -> None:
    """Verifies sliding deflection across multiple obstacles."""
    moving = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(0.5, 0.5, 0.5))
    obstacles = [
        BoundingBox(Vector3(3.0, 0.0, 0.0), Vector3(0.5, 2.0, 0.5)),
        BoundingBox(Vector3(0.0, 3.0, 0.0), Vector3(2.0, 0.5, 0.5)),
    ]
    velocity = Vector3(4.0, 2.0, 0.0)

    res = SweptAABBEngine.resolve_kinematic_step(moving, velocity, obstacles)
    for obstacle in obstacles:
        final_box = BoundingBox(res.final_position, moving.extent)
        assert not final_box.intersects(obstacle)


def test_dynamic_vs_dynamic_relative_motion() -> None:
    """Verifies collision between two moving entities using relative velocity."""
    box_a = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(0.5, 0.5, 0.5))
    box_b = BoundingBox(Vector3(5.0, 0.0, 0.0), Vector3(0.5, 0.5, 0.5))
    vel_a = Vector3(3.0, 0.0, 0.0)
    vel_b = Vector3(-2.0, 0.0, 0.0)

    hit = SweptAABBEngine.test_dynamic_vs_dynamic(box_a, vel_a, box_b, vel_b)
    assert hit.has_collision
    assert abs(hit.time_of_impact - 0.8) < 1e-5


def test_verifier_suite_execution() -> None:
    """Verifies that all invariant checks pass in formal verifier."""
    report = KinematicCcdVerifier.run_all_checks()
    assert report.all_passed
    assert report.checks_run == 6
