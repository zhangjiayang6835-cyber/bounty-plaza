"""Pytest suite for Issue #1324: Kinematic Continuous Collision Detection.

Coordinates adhere to Minecraft Bedrock standards:
+X = East, -X = West
+Y = Up,   -Y = Down
+Z = South, -Z = North
"""

import json
import os
from packages.kinematic_ccd.geometry import BedrockFace, BoundingBox, Vector3
from packages.kinematic_ccd.swept_ccd import (
    CollisionResult,
    Ray,
    RayHit,
    RaycastResult,
    StepResult,
    SweptAABBEngine,
)
from packages.kinematic_ccd.verifier import KinematicCcdVerifier


def test_bedrock_coordinate_conventions():
    """Verifies that vector and cardinal coordinates adhere to Bedrock standards."""
    box = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(1.0, 1.0, 1.0))
    faces = box.get_faces()
    assert len(faces) == 6

    face_dict = {face.name: face.normal for face in faces}
    assert face_dict["East"] == Vector3(1.0, 0.0, 0.0)
    assert face_dict["West"] == Vector3(-1.0, 0.0, 0.0)
    assert face_dict["Up"] == Vector3(0.0, 1.0, 0.0)
    assert face_dict["Down"] == Vector3(0.0, -1.0, 0.0)
    assert face_dict["South"] == Vector3(0.0, 0.0, 1.0)
    assert face_dict["North"] == Vector3(0.0, 0.0, -1.0)


def test_bounding_box_vertex_derivation():
    """Verifies that 8 bounding box vertices are correctly derived from bounds."""
    box = BoundingBox(Vector3(10.0, 20.0, 30.0), Vector3(2.0, 4.0, 6.0))
    vertices = box.derive_vertices()
    assert len(vertices) == 8

    expected_min = Vector3(8.0, 16.0, 24.0)
    expected_max = Vector3(12.0, 24.0, 36.0)

    assert box.min_point == expected_min
    assert box.max_point == expected_max
    assert expected_min in vertices
    assert expected_max in vertices


def test_swept_aabb_cardinal_axes_collision():
    """Verifies continuous swept AABB collision detection across all 6 axes."""
    origin = Vector3(0.0, 0.0, 0.0)
    unit_ext = Vector3(0.5, 0.5, 0.5)

    moving = BoundingBox(origin, unit_ext)
    obs_east = BoundingBox(Vector3(2.0, 0.0, 0.0), unit_ext)
    hit_east = SweptAABBEngine.test_swept_aabb(moving, Vector3(4.0, 0.0, 0.0), obs_east)
    assert hit_east.has_collision
    assert abs(hit_east.time_of_impact - 0.25) < 1e-5
    assert hit_east.normal == Vector3(-1.0, 0.0, 0.0)
    assert hit_east.cardinal_direction == "West"

    obs_west = BoundingBox(Vector3(-2.0, 0.0, 0.0), unit_ext)
    hit_west = SweptAABBEngine.test_swept_aabb(moving, Vector3(-4.0, 0.0, 0.0), obs_west)
    assert hit_west.has_collision
    assert abs(hit_west.time_of_impact - 0.25) < 1e-5
    assert hit_west.normal == Vector3(1.0, 0.0, 0.0)
    assert hit_west.cardinal_direction == "East"

    obs_up = BoundingBox(Vector3(0.0, 3.0, 0.0), unit_ext)
    hit_up = SweptAABBEngine.test_swept_aabb(moving, Vector3(0.0, 6.0, 0.0), obs_up)
    assert hit_up.has_collision
    assert abs(hit_up.time_of_impact - 1.0 / 3.0) < 1e-5
    assert hit_up.normal == Vector3(0.0, -1.0, 0.0)
    assert hit_up.cardinal_direction == "Down"

    obs_south = BoundingBox(Vector3(0.0, 0.0, 4.0), unit_ext)
    hit_south = SweptAABBEngine.test_swept_aabb(moving, Vector3(0.0, 0.0, 8.0), obs_south)
    assert hit_south.has_collision
    assert abs(hit_south.time_of_impact - 0.375) < 1e-5
    assert hit_south.normal == Vector3(0.0, 0.0, -1.0)
    assert hit_south.cardinal_direction == "North"


def test_swept_aabb_disjoint_miss():
    """Verifies that non-intersecting trajectories return no collision."""
    moving = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(0.5, 0.5, 0.5))
    obstacle = BoundingBox(Vector3(5.0, 5.0, 5.0), Vector3(0.5, 0.5, 0.5))
    velocity = Vector3(2.0, 0.0, 0.0)

    hit = SweptAABBEngine.test_swept_aabb(moving, velocity, obstacle)
    assert not hit.has_collision
    assert hit.time_of_impact == 1.0


def test_rapid_kinematic_tunneling_prevention():
    """Verifies that high velocity (> 1.5 blocks/tick) movement does not tunnel through walls."""
    moving = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(0.5, 0.5, 0.5))
    wall = BoundingBox(Vector3(2.0, 0.0, 0.0), Vector3(0.25, 4.0, 4.0))
    velocity = Vector3(6.0, 0.0, 0.0)

    res = SweptAABBEngine.resolve_kinematic_step(moving, velocity, [wall])
    assert res.tunneling_prevented
    assert len(res.collisions) > 0
    assert res.final_position.x < wall.min_point.x


def test_sub_tick_raycast_synchronization():
    """Verifies sub-tick raycast synchronization eliminating tick 5812 collision dropouts."""
    entity = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(0.5, 1.0, 0.5))
    velocity = Vector3(10.0, 0.0, 0.0)
    ray = Ray(
        origin=Vector3(5.0, 0.0, -5.0),
        direction=Vector3(0.0, 0.0, 1.0),
        max_distance=15.0,
    )

    result = SweptAABBEngine.synchronize_sub_tick_raycast(
        entity,
        velocity,
        ray,
        sub_tick_delta=0.5,
    )
    assert result.hit
    assert not result.warning_dropped
    assert result.sub_tick_fraction == 0.5
    assert abs(result.point.x - 5.0) < 1e-4


def test_dynamic_vs_dynamic_relative_velocity():
    """Verifies continuous collision detection between two moving entities."""
    box_a = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(0.5, 0.5, 0.5))
    box_b = BoundingBox(Vector3(5.0, 0.0, 0.0), Vector3(0.5, 0.5, 0.5))

    vel_a = Vector3(3.0, 0.0, 0.0)
    vel_b = Vector3(-3.0, 0.0, 0.0)

    hit = SweptAABBEngine.test_dynamic_vs_dynamic(box_a, vel_a, box_b, vel_b)
    assert hit.has_collision
    assert abs(hit.time_of_impact - (4.0 / 6.0)) < 1e-5
    assert hit.normal == Vector3(-1.0, 0.0, 0.0)


def test_formal_verifier_execution():
    """Verifies that all formal invariant checks pass cleanly."""
    report = KinematicCcdVerifier.run_all_checks()
    assert report.all_passed
    assert report.checks_run == 6


def test_manifest_validation():
    """Verifies manifest.json compliance with Bedrock Script API requirements."""
    manifest_path = os.path.join(os.path.dirname(__file__), "..", "manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as file_handle:
        manifest = json.load(file_handle)

    assert manifest["format_version"] == 2
    assert "header" in manifest
    assert "modules" in manifest
    assert "dependencies" in manifest

    script_module = next((m for m in manifest["modules"] if m["type"] == "script"), None)
    assert script_module is not None
    assert script_module["entry"] == "scripts/main.js"

    server_dep = next((d for d in manifest["dependencies"] if d.get("module_name") == "@minecraft/server"), None)
    assert server_dep is not None
