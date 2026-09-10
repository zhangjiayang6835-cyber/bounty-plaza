"""Formal invariant verifier for Hitbox Math and Continuous Collision Detection.

Coordinates adhere strictly to Minecraft Bedrock standards:
+X = East,  -X = West
+Y = Up,    -Y = Down
+Z = South, -Z = North
"""

from __future__ import annotations

import time
from dataclasses import dataclass

try:
    from packages.hitbox_math.geometry import BedrockFace, BoundingBox, Vector3
    from packages.hitbox_math.swept_ccd import HitboxCcdEngine
except (ImportError, ModuleNotFoundError):
    from geometry import BedrockFace, BoundingBox, Vector3
    from swept_ccd import HitboxCcdEngine


@dataclass(frozen=True)
class VerificationReport:
    """Consolidated outcome of formal invariant verification."""

    all_passed: bool
    checks_run: int
    details: tuple[str, ...]


class HitboxMathVerifier:
    """Formal verification engine enforcing Bedrock math invariants."""

    EPSILON = 1e-5

    @classmethod
    def run_all_checks(cls) -> VerificationReport:
        """Executes all formal invariant checks and returns consolidation report."""
        checks = (
            cls.verify_bedrock_coordinates(),
            cls.verify_vertex_derivation(),
            cls.verify_swept_toi_and_normals(),
            cls.verify_high_velocity_tunneling_prevention(),
            cls.verify_tick_4192_raycast_resolution(),
            cls.verify_multi_obstacle_sliding_resolution(),
            cls.verify_tick_budget_performance(),
        )

        all_passed = True
        notes: list[str] = []
        for passed, desc in checks:
            if not passed:
                all_passed = False
            notes.append(desc)

        return VerificationReport(
            all_passed=all_passed,
            checks_run=len(checks),
            details=tuple(notes),
        )

    @classmethod
    def verify_bedrock_coordinates(cls) -> tuple[bool, str]:
        """Validates cardinal directions against Bedrock coordinate standards."""
        box = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(1.0, 1.0, 1.0))
        faces = box.get_faces()

        for face in faces:
            if not cls._is_cardinal_face_valid(face):
                return False, f"Invalid face: {face.name}"

        return True, "Bedrock coordinates verified (+X East, +Y Up, +Z South)"

    @classmethod
    def _is_cardinal_face_valid(cls, face: BedrockFace) -> bool:
        """Validates surface normal orientation of cardinal face."""
        expected_normals = {
            "East": (1.0, 0.0, 0.0),
            "West": (-1.0, 0.0, 0.0),
            "Up": (0.0, 1.0, 0.0),
            "Down": (0.0, -1.0, 0.0),
            "South": (0.0, 0.0, 1.0),
            "North": (0.0, 0.0, -1.0),
        }
        if face.name not in expected_normals:
            return False
        exp = expected_normals[face.name]
        return (
            abs(face.normal.x - exp[0]) < cls.EPSILON
            and abs(face.normal.y - exp[1]) < cls.EPSILON
            and abs(face.normal.z - exp[2]) < cls.EPSILON
        )

    @classmethod
    def verify_vertex_derivation(cls) -> tuple[bool, str]:
        """Validates derivation of eight exact bounding box corner vertices."""
        box = BoundingBox(Vector3(10.0, 20.0, 30.0), Vector3(2.0, 4.0, 6.0))
        vertices = box.derive_vertices()
        if len(vertices) != 8:
            return False, "Vertex count mismatch"

        expected_min = Vector3(8.0, 16.0, 24.0)
        expected_max = Vector3(12.0, 24.0, 36.0)

        min_found = any(cls._vec_equals(v, expected_min) for v in vertices)
        max_found = any(cls._vec_equals(v, expected_max) for v in vertices)

        if not min_found or not max_found:
            return False, "Vertex boundary mismatch"

        return True, "8-vertex derivation verified across exact extents"

    @classmethod
    def verify_swept_toi_and_normals(cls) -> tuple[bool, str]:
        """Validates continuous swept AABB time of impact and normal vector."""
        moving = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(1.0, 1.0, 1.0))
        obstacle = BoundingBox(Vector3(5.0, 0.0, 0.0), Vector3(1.0, 1.0, 1.0))
        velocity = Vector3(10.0, 0.0, 0.0)

        hit = HitboxCcdEngine.test_swept_aabb(moving, velocity, obstacle)
        if not hit.has_collision:
            return False, "Swept collision missed obstacle"

        expected_toi = 0.3
        if abs(hit.time_of_impact - expected_toi) > cls.EPSILON:
            return False, f"Unexpected TOI: {hit.time_of_impact}"

        if not cls._vec_equals(hit.normal, Vector3(-1.0, 0.0, 0.0)):
            return False, f"Unexpected normal: {hit.normal}"

        return True, "Swept AABB TOI (0.30) and normal (West) verified"

    @classmethod
    def verify_high_velocity_tunneling_prevention(cls) -> tuple[bool, str]:
        """Validates that rapid kinematic motion (>1.5 blocks/tick) prevents tunneling."""
        moving = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(1.0, 1.0, 1.0))
        wall = BoundingBox(Vector3(2.0, 0.0, 0.0), Vector3(0.5, 5.0, 5.0))
        velocity = Vector3(5.0, 0.0, 0.0)

        res = HitboxCcdEngine.resolve_kinematic_step(moving, velocity, [wall])
        if not res.tunneling_prevented:
            return False, "Tunneling flag not set"

        if res.final_position.x >= wall.min_point.x:
            return False, "Penetration detected through wall"

        return True, "Tunneling prevention verified at 5.0 blocks/tick"

    @classmethod
    def verify_tick_4192_raycast_resolution(cls) -> tuple[bool, str]:
        """Validates resolution of tick 4192 raycast miss warning from issue log."""
        res = HitboxCcdEngine.validate_tick_4192_raycast()
        if not res.hit:
            return False, "Tick 4192 raycast missed target volume"

        if not res.warning_miss_resolved:
            return False, "Tick 4192 warning not resolved"

        if res.tick != 4192:
            return False, f"Unexpected tick: {res.tick}"

        return True, "Tick 4192 raycast miss resolved with parametric hit validation"

    @classmethod
    def verify_multi_obstacle_sliding_resolution(cls) -> tuple[bool, str]:
        """Validates sliding deflection along multiple collision surface normals."""
        moving = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(0.5, 0.5, 0.5))
        obstacles = [
            BoundingBox(Vector3(3.0, 0.0, 0.0), Vector3(0.5, 2.0, 0.5)),
            BoundingBox(Vector3(0.0, 3.0, 0.0), Vector3(2.0, 0.5, 0.5)),
        ]
        velocity = Vector3(4.0, 2.0, 0.0)

        res = HitboxCcdEngine.resolve_kinematic_step(moving, velocity, obstacles)
        for obstacle in obstacles:
            final_box = BoundingBox(res.final_position, moving.extent)
            if final_box.intersects(obstacle):
                return False, "Multi-obstacle step resulted in penetration"

        return True, "Multi-obstacle kinematic sliding deflection verified"

    @classmethod
    def verify_tick_budget_performance(cls) -> tuple[bool, str]:
        """Validates calculation efficiency to prevent Script API tick budget throttling."""
        moving = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(0.5, 0.5, 0.5))
        obs = BoundingBox(Vector3(2.0, 0.0, 0.0), Vector3(0.5, 0.5, 0.5))
        vel = Vector3(4.0, 0.0, 0.0)

        start_time = time.perf_counter()
        for _ in range(100):
            HitboxCcdEngine.test_swept_aabb(moving, vel, obs)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        if elapsed_ms > 5.0:
            return False, f"Tick budget exceeded: {elapsed_ms:.2f}ms"

        return True, f"Tick budget verified: 100 entity steps in {elapsed_ms:.2f}ms (<5ms limit)"

    @classmethod
    def _vec_equals(cls, vec_a: Vector3, vec_b: Vector3) -> bool:
        """Determines approximate equality between two 3D vectors."""
        return (
            abs(vec_a.x - vec_b.x) < cls.EPSILON
            and abs(vec_a.y - vec_b.y) < cls.EPSILON
            and abs(vec_a.z - vec_b.z) < cls.EPSILON
        )


if __name__ == "__main__":
    report = HitboxMathVerifier.run_all_checks()
    for item in report.details:
        print(f"[*] {item}")
    if not report.all_passed:
        raise SystemExit(1)
    print(f"\nAll {report.checks_run} formal invariant checks PASSED.")
