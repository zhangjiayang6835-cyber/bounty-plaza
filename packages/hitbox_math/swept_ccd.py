"""Swept AABB Continuous Collision Detection and kinematic synchronization engine.

Coordinates adhere strictly to Minecraft Bedrock standards:
+X = East,  -X = West
+Y = Up,    -Y = Down
+Z = South, -Z = North
"""

from __future__ import annotations

import math
from dataclasses import dataclass

try:
    from packages.hitbox_math.geometry import BoundingBox, Vector3
except (ImportError, ModuleNotFoundError):
    from geometry import BoundingBox, Vector3


EMPTY_VEC = Vector3(0.0, 0.0, 0.0)


@dataclass(frozen=True)
class Ray:
    """Parametric 3D ray for line-of-sight and projectile hit evaluation."""

    origin: Vector3
    direction: Vector3
    max_distance: float


@dataclass(frozen=True)
class RayHit:
    """Details of spatial ray collision against bounding volume."""

    hit: bool
    distance: float
    point: Vector3
    normal: Vector3


@dataclass(frozen=True)
class CollisionResult:
    """Outcome of continuous swept AABB intersection evaluation."""

    has_collision: bool
    time_of_impact: float
    normal: Vector3
    contact_point: Vector3
    cardinal_direction: str


@dataclass(frozen=True)
class RaycastResult:
    """Outcome of tick-interpolated parametric raycast hit validation."""

    hit: bool
    distance: float
    sub_tick_fraction: float
    point: Vector3
    normal: Vector3
    warning_miss_resolved: bool
    tick: int


@dataclass(frozen=True)
class StepResult:
    """Kinematic trajectory resolution against obstacle geometries."""

    final_position: Vector3
    final_velocity: Vector3
    collisions: tuple[CollisionResult, ...]
    tunneling_prevented: bool


@dataclass(frozen=True)
class AxisTimes:
    """Entry and exit intervals across all three spatial axes."""

    entry: Vector3
    exit: Vector3


@dataclass(frozen=True)
class AxisTimeResult:
    """Calculated entry time, exit time, and distance on a single axis."""

    disjoint: bool
    entry_time: float
    exit_time: float
    entry_dist: float


class HitboxCcdEngine:
    """Swept AABB Continuous Collision Detection and raycast synchronization."""

    EPSILON = 1e-6
    TUNNELING_VELOCITY_THRESHOLD = 1.5

    @classmethod
    def test_swept_aabb(
        cls,
        moving: BoundingBox,
        velocity: Vector3,
        obstacle: BoundingBox,
    ) -> CollisionResult:
        """Evaluates continuous swept collision between moving entity and obstacle."""
        no_hit = CollisionResult(False, 1.0, EMPTY_VEC, EMPTY_VEC, "")
        broadphase = moving.expand(velocity)
        if not broadphase.intersects(obstacle):
            return no_hit

        if moving.intersects(obstacle):
            return CollisionResult(True, 0.0, EMPTY_VEC, moving.center, "")

        is_disjoint, times, dists = cls._compute_axis_times(moving, obstacle, velocity)
        if is_disjoint:
            return no_hit

        entry_time = max(times.entry.x, times.entry.y, times.entry.z)
        exit_time = min(times.exit.x, times.exit.y, times.exit.z)

        if entry_time > exit_time or entry_time < 0.0 or entry_time > 1.0:
            return no_hit

        if times.entry.x < 0.0 and times.entry.y < 0.0 and times.entry.z < 0.0:
            return no_hit

        normal, cardinal = cls._determine_surface_normal(entry_time, times.entry, dists)
        hit_center = moving.center.add(velocity.scale(entry_time))
        contact_point = cls._clamp_contact_point(hit_center, obstacle)

        return CollisionResult(
            has_collision=True,
            time_of_impact=entry_time,
            normal=normal,
            contact_point=contact_point,
            cardinal_direction=cardinal,
        )

    @classmethod
    def test_dynamic_vs_dynamic(
        cls,
        box_a: BoundingBox,
        vel_a: Vector3,
        box_b: BoundingBox,
        vel_b: Vector3,
    ) -> CollisionResult:
        """Evaluates continuous collision between two moving entities via relative velocity."""
        relative_vel = vel_a.subtract(vel_b)
        return cls.test_swept_aabb(box_a, relative_vel, box_b)

    @classmethod
    def resolve_kinematic_step(
        cls,
        entity_box: BoundingBox,
        velocity: Vector3,
        obstacles: list[BoundingBox],
    ) -> StepResult:
        """Resolves multi-obstacle sliding deflection along contact surface normals."""
        current_box = entity_box
        remaining_vel = velocity
        final_position = entity_box.center
        collected_collisions: list[CollisionResult] = []

        tunneling_risk = velocity.magnitude() >= cls.TUNNELING_VELOCITY_THRESHOLD

        for _ in range(3):
            if remaining_vel.magnitude() < cls.EPSILON:
                break

            earliest_hit = cls._find_earliest_collision(current_box, remaining_vel, obstacles)
            if earliest_hit is None:
                final_position = current_box.center.add(remaining_vel)
                break

            collected_collisions.append(earliest_hit)
            safe_toi = max(0.0, earliest_hit.time_of_impact - cls.EPSILON)
            final_position = current_box.center.add(remaining_vel.scale(safe_toi))
            current_box = BoundingBox(final_position, current_box.extent)

            remaining_time = 1.0 - earliest_hit.time_of_impact
            remaining_vel = cls._deflect_velocity(
                remaining_vel,
                earliest_hit.normal,
                remaining_time,
            )

        has_hits = len(collected_collisions) > 0
        return StepResult(
            final_position=final_position,
            final_velocity=remaining_vel,
            collisions=tuple(collected_collisions),
            tunneling_prevented=tunneling_risk and has_hits,
        )

    @classmethod
    def synchronize_sub_tick_raycast(
        cls,
        entity_box: BoundingBox,
        velocity: Vector3,
        ray: Ray,
        sub_tick_delta: float = 0.5,
        tick: int = 4192,
    ) -> RaycastResult:
        """Validates parametric raycast against tick-interpolated and swept bounding volumes."""
        clamped_delta = max(0.0, min(1.0, sub_tick_delta))
        interpolated_center = entity_box.center.add(velocity.scale(clamped_delta))
        interpolated_box = BoundingBox(interpolated_center, entity_box.extent)

        inter_res = cls.intersect_ray_aabb(ray, interpolated_box)
        if inter_res.hit:
            return RaycastResult(
                hit=True,
                distance=inter_res.distance,
                sub_tick_fraction=clamped_delta,
                point=inter_res.point,
                normal=inter_res.normal,
                warning_miss_resolved=True,
                tick=tick,
            )

        swept_box = entity_box.expand(velocity)
        swept_res = cls.intersect_ray_aabb(ray, swept_box)
        if swept_res.hit:
            return RaycastResult(
                hit=True,
                distance=swept_res.distance,
                sub_tick_fraction=clamped_delta,
                point=swept_res.point,
                normal=swept_res.normal,
                warning_miss_resolved=True,
                tick=tick,
            )

        return RaycastResult(
            hit=False,
            distance=math.inf,
            sub_tick_fraction=clamped_delta,
            point=EMPTY_VEC,
            normal=EMPTY_VEC,
            warning_miss_resolved=False,
            tick=tick,
        )

    @classmethod
    def validate_tick_4192_raycast(cls) -> RaycastResult:
        """Specifically validates kinematic raycast parameters reported in tick 4192 log warning."""
        ray_origin = Vector3(102.4, 64.0, -12.1)
        ray_vector = Vector3(0.8, -0.2, 1.4)
        ray_dir = ray_vector.normalize()
        ray_len = ray_vector.magnitude() * 10.0

        ray = Ray(
            origin=ray_origin,
            direction=ray_dir,
            max_distance=ray_len,
        )

        entity_origin = Vector3(104.0, 63.5, -9.0)
        entity_extent = Vector3(1.0, 1.2, 1.0)
        entity_box = BoundingBox(entity_origin, entity_extent)
        entity_velocity = Vector3(1.8, -0.3, 2.5)

        return cls.synchronize_sub_tick_raycast(
            entity_box=entity_box,
            velocity=entity_velocity,
            ray=ray,
            sub_tick_delta=0.45,
            tick=4192,
        )

    @classmethod
    def intersect_ray_aabb(cls, ray: Ray, box: BoundingBox) -> RayHit:
        """Evaluates parametric ray intersection against stationary bounding volume."""
        has_hit, hit_dist, hit_normal = cls._evaluate_slabs(ray, box)
        if not has_hit:
            return RayHit(False, math.inf, EMPTY_VEC, EMPTY_VEC)
        hit_point = ray.origin.add(ray.direction.scale(hit_dist))
        return RayHit(True, hit_dist, hit_point, hit_normal)

    @classmethod
    def _evaluate_slabs(cls, ray: Ray, box: BoundingBox) -> tuple[bool, float, Vector3]:
        """Clips ray against 3D Axis-Aligned Bounding Box slabs."""
        t_min = 0.0
        t_max = ray.max_distance
        hit_normal = EMPTY_VEC

        slabs = (
            (ray.origin.x, ray.direction.x, box.min_point.x, box.max_point.x, Vector3(1, 0, 0)),
            (ray.origin.y, ray.direction.y, box.min_point.y, box.max_point.y, Vector3(0, 1, 0)),
            (ray.origin.z, ray.direction.z, box.min_point.z, box.max_point.z, Vector3(0, 0, 1)),
        )

        for origin, direction, min_b, max_b, norm_pos in slabs:
            slab = cls._test_slab(origin, direction, min_b, max_b, norm_pos)
            if not slab[0]:
                return False, 0.0, EMPTY_VEC
            if slab[1] > t_min:
                t_min = slab[1]
                hit_normal = slab[3]
            t_max = min(t_max, slab[2])
            if t_min > t_max:
                return False, 0.0, EMPTY_VEC

        if t_min > ray.max_distance or t_max < 0.0:
            return False, 0.0, EMPTY_VEC

        return True, max(0.0, t_min), hit_normal

    @classmethod
    def _test_slab(
        cls,
        origin: float,
        direction: float,
        min_bound: float,
        max_bound: float,
        norm_pos: Vector3,
    ) -> tuple[bool, float, float, Vector3]:
        """Computes 1D parametric entry and exit bounds for slab."""
        norm_neg = norm_pos.scale(-1.0)
        if abs(direction) < cls.EPSILON:
            if origin < min_bound or origin > max_bound:
                return False, 0.0, 0.0, EMPTY_VEC
            return True, -math.inf, math.inf, EMPTY_VEC

        time1 = (min_bound - origin) / direction
        time2 = (max_bound - origin) / direction
        if time1 > time2:
            return True, time2, time1, norm_pos
        return True, time1, time2, norm_neg

    @classmethod
    def _compute_single_axis_times(
        cls,
        min_m: float,
        max_m: float,
        min_o: float,
        max_o: float,
        vel: float,
    ) -> AxisTimeResult:
        """Calculates entry time, exit time, and distance for single coordinate axis."""
        entry_d = min_o - max_m if vel > 0.0 else max_o - min_m
        exit_d = max_o - min_m if vel > 0.0 else min_o - max_m

        if abs(vel) < cls.EPSILON:
            if max_m <= min_o or min_m >= max_o:
                return AxisTimeResult(True, 0.0, 0.0, 0.0)
            return AxisTimeResult(False, -math.inf, math.inf, 0.0)

        return AxisTimeResult(False, entry_d / vel, exit_d / vel, entry_d)

    @classmethod
    def _compute_axis_times(
        cls,
        moving: BoundingBox,
        obstacle: BoundingBox,
        velocity: Vector3,
    ) -> tuple[bool, AxisTimes, Vector3]:
        """Calculates 3D entry and exit parametric times across XYZ axes."""
        res_x = cls._compute_single_axis_times(
            moving.min_point.x,
            moving.max_point.x,
            obstacle.min_point.x,
            obstacle.max_point.x,
            velocity.x,
        )
        if res_x.disjoint:
            return True, AxisTimes(EMPTY_VEC, EMPTY_VEC), EMPTY_VEC

        res_y = cls._compute_single_axis_times(
            moving.min_point.y,
            moving.max_point.y,
            obstacle.min_point.y,
            obstacle.max_point.y,
            velocity.y,
        )
        if res_y.disjoint:
            return True, AxisTimes(EMPTY_VEC, EMPTY_VEC), EMPTY_VEC

        res_z = cls._compute_single_axis_times(
            moving.min_point.z,
            moving.max_point.z,
            obstacle.min_point.z,
            obstacle.max_point.z,
            velocity.z,
        )
        if res_z.disjoint:
            return True, AxisTimes(EMPTY_VEC, EMPTY_VEC), EMPTY_VEC

        times = AxisTimes(
            Vector3(res_x.entry_time, res_y.entry_time, res_z.entry_time),
            Vector3(res_x.exit_time, res_y.exit_time, res_z.exit_time),
        )
        return False, times, Vector3(res_x.entry_dist, res_y.entry_dist, res_z.entry_dist)

    @classmethod
    def _determine_surface_normal(
        cls,
        entry_time: float,
        entry_times: Vector3,
        entry_dists: Vector3,
    ) -> tuple[Vector3, str]:
        """Determines collision normal and cardinal face name from entry axis."""
        if entry_time == entry_times.x:
            if entry_dists.x < 0.0:
                return Vector3(1.0, 0.0, 0.0), "East"
            return Vector3(-1.0, 0.0, 0.0), "West"
        if entry_time == entry_times.y:
            if entry_dists.y < 0.0:
                return Vector3(0.0, 1.0, 0.0), "Up"
            return Vector3(0.0, -1.0, 0.0), "Down"
        if entry_dists.z < 0.0:
            return Vector3(0.0, 0.0, 1.0), "South"
        return Vector3(0.0, 0.0, -1.0), "North"

    @classmethod
    def _clamp_contact_point(cls, hit_center: Vector3, obstacle: BoundingBox) -> Vector3:
        """Clamps center coordinates to obstacle surface bounds."""
        contact_x = max(obstacle.min_point.x, min(obstacle.max_point.x, hit_center.x))
        contact_y = max(obstacle.min_point.y, min(obstacle.max_point.y, hit_center.y))
        contact_z = max(obstacle.min_point.z, min(obstacle.max_point.z, hit_center.z))
        return Vector3(contact_x, contact_y, contact_z)

    @classmethod
    def _find_earliest_collision(
        cls,
        current_box: BoundingBox,
        remaining_vel: Vector3,
        obstacles: list[BoundingBox],
    ) -> CollisionResult | None:
        """Finds earliest obstacle collision within current trajectory segment."""
        earliest_hit: CollisionResult | None = None
        for obstacle in obstacles:
            hit = cls.test_swept_aabb(current_box, remaining_vel, obstacle)
            if hit.has_collision:
                if earliest_hit is None or hit.time_of_impact < earliest_hit.time_of_impact:
                    earliest_hit = hit
        return earliest_hit

    @classmethod
    def _deflect_velocity(
        cls,
        velocity: Vector3,
        normal: Vector3,
        remaining_time: float,
    ) -> Vector3:
        """Computes deflected velocity vector along obstacle collision plane."""
        normal_dot = velocity.dot(normal)
        deflected_x = (velocity.x - normal_dot * normal.x) * remaining_time
        deflected_y = (velocity.y - normal_dot * normal.y) * remaining_time
        deflected_z = (velocity.z - normal_dot * normal.z) * remaining_time
        return Vector3(deflected_x, deflected_y, deflected_z)
