"""Formal verifier for Kinematic Continuous Collision Detection engine.

Coordinates adhere to Minecraft Bedrock conventions:
+X = East, -X = West
+Y = Up,   -Y = Down
+Z = South, -Z = North
"""

from dataclasses import dataclass
try:
    from packages.kinematic_ccd.geometry import BedrockFace, BoundingBox, Vector3
    from packages.kinematic_ccd.swept_ccd import Ray, SweptAABBEngine
except (ImportError, ModuleNotFoundError):
    from geometry import BedrockFace, BoundingBox, Vector3
    from swept_ccd import Ray, SweptAABBEngine


@dataclass(frozen=True)
class VerificationReport:
    """Report outcome of formal invariant verification."""

    all_passed: bool
    checks_run: int
    details: tuple[str, ...]


class KinematicCcdVerifier:
    """Invariant validation suite for continuous kinematic collision detection."""

    EPSILON = 1e-5

    @classmethod
    def run_all_checks(cls) -> VerificationReport:
        """Executes all formal invariant checks and returns comprehensive report."""
        checks = (
            cls.verify_bedrock_coordinates(),
            cls.verify_vertex_derivation(),
            cls.verify_swept_toi_and_normals(),
            cls.verify_high_velocity_tunneling_prevention(),
            cls.verify_sub_tick_raycast_synchronization(),
            cls.verify_multi_obstacle_kinematic_resolution(),
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
        """Validates cardinal directions against Minecraft Bedrock coordinate rules."""
        box = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(1.0, 1.0, 1.0))
        faces = box.get_faces()

        for face in faces:
            if not cls._is_cardinal_face_valid(face):
                return False, f"Invalid Bedrock face configuration: {face.name}"

        return True, "Bedrock coordinates verified: +X East, +Y Up, +Z South"

    @classmethod
    def _is_cardinal_face_valid(cls, face: BedrockFace) -> bool:
        """Checks cardinal face normal mapping."""
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
        """Validates 8-vertex bounding box corner derivation."""
        box = BoundingBox(Vector3(10.0, 20.0, 30.0), Vector3(2.0, 4.0, 6.0))
        vertices = box.derive_vertices()
        if len(vertices) != 8:
            return False, "Bounding box does not contain exactly 8 vertices"

        expected_min = Vector3(8.0, 16.0, 24.0)
        expected_max = Vector3(12.0, 24.0, 36.0)

        min_found = any(cls._vec_equals(v, expected_min) for v in vertices)
        max_found = any(cls._vec_equals(v, expected_max) for v in vertices)

        if not min_found or not max_found:
            return False, "Vertex extents do not match expected bounds"

        return True, "8-vertex derivation verified with exact coordinate boundaries"

    @classmethod
    def verify_swept_toi_and_normals(cls) -> tuple[bool, str]:
        """Validates swept AABB time of impact and collision normal orientation."""
        moving = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(1.0, 1.0, 1.0))
        obstacle = BoundingBox(Vector3(5.0, 0.0, 0.0), Vector3(1.0, 1.0, 1.0))
        velocity = Vector3(10.0, 0.0, 0.0)

        hit = SweptAABBEngine.test_swept_aabb(moving, velocity, obstacle)
        if not hit.has_collision:
            return False, "Expected collision along X axis was not detected"

        expected_toi = 0.3
        if abs(hit.time_of_impact - expected_toi) > cls.EPSILON:
            return False, f"Incorrect TOI: got {hit.time_of_impact}, expected {expected_toi}"

        if not cls._vec_equals(hit.normal, Vector3(-1.0, 0.0, 0.0)):
            return False, f"Incorrect normal: got {hit.normal}, expected West (-1, 0, 0)"

        return True, "Swept AABB TOI and normal verified (TOI: 0.30, normal: West)"

    @classmethod
    def verify_high_velocity_tunneling_prevention(cls) -> tuple[bool, str]:
        """Validates prevention of tunneling at velocities above 1.5 blocks/tick."""
        moving = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(1.0, 1.0, 1.0))
        wall = BoundingBox(Vector3(2.0, 0.0, 0.0), Vector3(0.5, 5.0, 5.0))
        velocity = Vector3(5.0, 0.0, 0.0)

        res = SweptAABBEngine.resolve_kinematic_step(moving, velocity, [wall])
        if not res.tunneling_prevented:
            return False, "Tunneling prevention flag was not asserted"

        if res.final_position.x >= wall.min_point.x:
            return False, "Moving box penetrated through the obstacle wall"

        return True, "High-velocity tunneling prevention verified at 5.0 blocks/tick"

    @classmethod
    def verify_sub_tick_raycast_synchronization(cls) -> tuple[bool, str]:
        """Validates sub-tick raycast synchronization eliminating tick 5812 dropouts."""
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
        if not res.hit:
            return False, "Sub-tick raycast failed to hit interpolated entity volume"

        if res.warning_dropped:
            return False, "Sub-tick raycast flagged warning_dropped"

        return True, "Sub-tick raycast synchronization verified: warning_dropped=False"

    @classmethod
    def verify_multi_obstacle_kinematic_resolution(cls) -> tuple[bool, str]:
        """Validates sliding resolution across multiple spatial obstacles."""
        moving = BoundingBox(Vector3(0.0, 0.0, 0.0), Vector3(0.5, 0.5, 0.5))
        obstacles = [
            BoundingBox(Vector3(3.0, 0.0, 0.0), Vector3(0.5, 2.0, 0.5)),
            BoundingBox(Vector3(0.0, 3.0, 0.0), Vector3(2.0, 0.5, 0.5)),
        ]
        velocity = Vector3(4.0, 2.0, 0.0)

        res = SweptAABBEngine.resolve_kinematic_step(moving, velocity, obstacles)
        for obstacle in obstacles:
            final_box = BoundingBox(res.final_position, moving.extent)
            if final_box.intersects(obstacle):
                return False, "Kinematic step resulted in obstacle penetration"

        return True, "Multi-obstacle kinematic sliding resolution verified"

    @classmethod
    def _vec_equals(cls, vec_a: Vector3, vec_b: Vector3) -> bool:
        """Checks whether two 3D vectors are approximately equal."""
        return (
            abs(vec_a.x - vec_b.x) < cls.EPSILON
            and abs(vec_a.y - vec_b.y) < cls.EPSILON
            and abs(vec_a.z - vec_b.z) < cls.EPSILON
        )


if __name__ == "__main__":
    report = KinematicCcdVerifier.run_all_checks()
    for item in report.details:
        print(f"[*] {item}")
    if not report.all_passed:
        raise SystemExit(1)
    print(f"\nAll {report.checks_run} kinematic invariant checks PASSED.")
