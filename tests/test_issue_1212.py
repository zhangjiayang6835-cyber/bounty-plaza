"""Unit and integration test suite for Issue #1212 Kinematics Solver and Collision Guard."""

from __future__ import annotations

import math
import pytest
from packages.kinematics_solver.models import (
    Vector3D,
    KinematicState,
    ColliderBox,
)
from packages.kinematics_solver.rk4_integrator import RungeKutta4Integrator
from packages.kinematics_solver.kalman_filter import KinematicKalmanFilter
from packages.kinematics_solver.collision_guard import CollisionDropoutGuard
from packages.kinematics_solver.root_cause_analyzer import RootCauseAnalyzer


def test_vector3d_arithmetic() -> None:
    """Verify basic vector algebra operations."""
    v1 = Vector3D(1.0, 2.0, 3.0)
    v2 = Vector3D(4.0, 5.0, 6.0)

    v_sum = v1 + v2
    assert v_sum == Vector3D(5.0, 7.0, 9.0)

    v_diff = v2 - v1
    assert v_diff == Vector3D(3.0, 3.0, 3.0)

    v_scaled = v1 * 2.5
    assert v_scaled == Vector3D(2.5, 5.0, 7.5)

    v_rscaled = 2.0 * v1
    assert v_rscaled == Vector3D(2.0, 4.0, 6.0)

    v_div = v2 / 2.0
    assert v_div == Vector3D(2.0, 2.5, 3.0)

    dot = v1.dot(v2)
    assert dot == pytest.approx(1.0 * 4.0 + 2.0 * 5.0 + 3.0 * 6.0)

    norm = Vector3D(3.0, 4.0, 0.0).norm()
    assert norm == pytest.approx(5.0)

    dist = v1.distance_to(v2)
    assert dist == pytest.approx(math.sqrt(27.0))


def test_vector3d_division_by_zero() -> None:
    """Verify that division by near-zero raises ZeroDivisionError."""
    v = Vector3D(1.0, 1.0, 1.0)
    with pytest.raises(ZeroDivisionError):
        _ = v / 0.0


def test_vector3d_serialization() -> None:
    """Verify dictionary serialization and deserialization."""
    v = Vector3D(12.5, -3.4, 0.75)
    data = v.to_dict()
    assert data == {"x": 12.5, "y": -3.4, "z": 0.75}

    v_reconstructed = Vector3D.from_dict(data)
    assert v_reconstructed == v


def test_kinematic_state_initialization() -> None:
    """Verify default initial state creation."""
    pos = Vector3D(0.0, 64.0, 0.0)
    state = KinematicState.initial(pos)
    assert state.position == pos
    assert state.velocity == Vector3D(0.0, 0.0, 0.0)
    assert state.acceleration == Vector3D(0.0, 0.0, 0.0)
    assert state.timestamp == 0.0


def test_rk4_constant_acceleration() -> None:
    """Verify RK4 integration matches analytical kinematics under constant acceleration."""
    initial_state = KinematicState.initial(
        pos=Vector3D(0.0, 10.0, 0.0),
        vel=Vector3D(0.0, 5.0, 0.0),
        acc=Vector3D(0.0, 2.0, 0.0),
    )

    def constant_accel(_t: float, _p: Vector3D, _v: Vector3D) -> Vector3D:
        return Vector3D(0.0, 2.0, 0.0)

    dt = 0.05
    total_time = 2.0
    trajectory = RungeKutta4Integrator.simulate_trajectory(
        initial_state, total_time, dt, constant_accel
    )

    final_state = trajectory[-1]
    expected_y = 10.0 + 5.0 * total_time + 0.5 * 2.0 * (total_time ** 2)
    expected_vy = 5.0 + 2.0 * total_time

    assert final_state.position.y == pytest.approx(expected_y, abs=1e-9)
    assert final_state.velocity.y == pytest.approx(expected_vy, abs=1e-9)


def test_rk4_harmonic_oscillator() -> None:
    """Verify RK4 numerical stability on a harmonic oscillator system."""
    omega = 2.0
    init_state = KinematicState.initial(
        pos=Vector3D(1.0, 0.0, 0.0),
        vel=Vector3D(0.0, 0.0, 0.0),
    )

    def oscillator_accel(_t: float, p: Vector3D, _v: Vector3D) -> Vector3D:
        return Vector3D(-(omega ** 2) * p.x, 0.0, 0.0)

    dt = 0.01
    duration = 3.14159265
    traj = RungeKutta4Integrator.simulate_trajectory(init_state, duration, dt, oscillator_accel)

    final_state = traj[-1]
    expected_x = math.cos(omega * duration)
    assert final_state.position.x == pytest.approx(expected_x, abs=1e-4)


def test_rk4_convergence_dt_0_05() -> None:
    """Verify fourth-order convergence under standard discrete tick delta dt = 0.05s."""
    metrics = RungeKutta4Integrator.verify_convergence(step_size=0.05, total_duration=1.0)
    assert metrics.converged
    assert metrics.max_absolute_error < 1e-6
    assert metrics.estimated_order >= 3.8


def test_kalman_filter_state_prediction() -> None:
    """Verify Kalman filter prediction mechanics."""
    kf = KinematicKalmanFilter(
        initial_position=Vector3D(0.0, 0.0, 0.0),
        initial_velocity=Vector3D(0.0, 10.0, 0.0),
    )
    kf.predict(dt=0.05)

    assert kf.position.y == pytest.approx(0.5, abs=1e-3)
    assert kf.velocity.y == pytest.approx(10.0, abs=1e-3)


def test_kalman_filter_measurement_update() -> None:
    """Verify Kalman filter state correction using noisy measurements."""
    kf = KinematicKalmanFilter(
        initial_position=Vector3D(0.0, 0.0, 0.0),
        initial_velocity=Vector3D(0.0, 1.0, 0.0),
    )

    for i in range(10):
        t = (i + 1) * 0.05
        true_pos = Vector3D(0.0, t * 1.0, 0.0)
        kf.predict(dt=0.05)
        kf.update(true_pos)

    assert kf.position.y == pytest.approx(0.5, abs=0.02)
    assert kf.velocity.y == pytest.approx(1.0, abs=0.05)


def test_kalman_filter_subtick_extrapolation() -> None:
    """Verify sub-tick coordinate extrapolation for network interpolation."""
    kf = KinematicKalmanFilter(
        initial_position=Vector3D(0.0, 10.0, 0.0),
        initial_velocity=Vector3D(0.0, 20.0, 0.0),
    )
    extrapolated = kf.extrapolate(forward_dt=0.025)
    assert extrapolated.y == pytest.approx(10.5, abs=1e-4)


def test_collider_box_containment_and_intersection() -> None:
    """Verify AABB volume containment and intersection detection."""
    box1 = ColliderBox(
        min_point=Vector3D(0.0, 0.0, 0.0),
        max_point=Vector3D(1.0, 1.0, 1.0),
    )
    box2 = ColliderBox(
        min_point=Vector3D(0.5, 0.5, 0.5),
        max_point=Vector3D(1.5, 1.5, 1.5),
    )
    box3 = ColliderBox(
        min_point=Vector3D(2.0, 2.0, 2.0),
        max_point=Vector3D(3.0, 3.0, 3.0),
    )

    assert box1.contains(Vector3D(0.5, 0.5, 0.5))
    assert not box1.contains(Vector3D(1.5, 0.5, 0.5))
    assert box1.intersects(box2)
    assert not box1.intersects(box3)
    assert box1.top_face_y() == 1.0


def test_collision_dropout_guard_support_detection() -> None:
    """Verify proper support detection when player stands on shulker top face."""
    guard = CollisionDropoutGuard()
    shulker_base = Vector3D(0.0, 10.0, 0.0)
    player_feet = Vector3D(0.0, 11.0, 0.0)

    contact = guard.evaluate_contact(player_feet, shulker_base)
    assert contact.is_supported
    assert contact.normal == Vector3D(0.0, 1.0, 0.0)
    assert contact.separation_distance == pytest.approx(0.0)


def test_collision_dropout_guard_high_speed_ascent() -> None:
    """Verify zero collision dropouts during rapid upward ascent."""
    guard = CollisionDropoutGuard()
    dt = 0.05
    duration = 2.0

    for ascent_speed in [10.0, 25.0, 50.0]:
        init_state = KinematicState.initial(
            pos=Vector3D(0.0, 10.0, 0.0),
            vel=Vector3D(0.0, ascent_speed, 0.0),
        )

        def ascent_accel(_t: float, _p: Vector3D, _v: Vector3D) -> Vector3D:
            return Vector3D(0.0, 0.0, 0.0)

        traj = RungeKutta4Integrator.simulate_trajectory(init_state, duration, dt, ascent_accel)
        initial_player = Vector3D(0.0, 11.0, 0.0)

        telemetry = guard.simulate_ascent(traj, initial_player)
        assert telemetry["zero_dropout_verified"]
        assert telemetry["dropouts"] == 0
        assert telemetry["dropout_rate"] == 0.0


def test_root_cause_effect_spam_analysis() -> None:
    """Verify root cause diagnosis of per-tick addEffect calls."""
    analysis = RootCauseAnalyzer.analyze_effect_spam(tick_count=100)
    assert analysis["is_pathological"]
    assert analysis["packets_broadcast"] == 100
    assert analysis["component_invalidations"] == 100
    assert analysis["redundancy_ratio"] > 0.98


def test_root_cause_floor_truncation_analysis() -> None:
    """Verify root cause diagnosis of Math.floor coordinate truncation."""
    dt = 0.05
    v_y = 12.37
    trajectory = [10.0 + v_y * (i * dt) for i in range(40)]

    analysis = RootCauseAnalyzer.analyze_floor_truncation(trajectory)
    assert analysis["causes_surface_separation"]
    assert analysis["max_truncation_error"] > 0.005
    assert analysis["downward_snaps"] > 0


def test_end_to_end_telemetry_evaluation() -> None:
    """Verify comprehensive comparative telemetry between flawed and fixed pipelines."""
    dt = 0.05
    v_y = 15.0
    trajectory = [20.0 + v_y * (i * dt) for i in range(50)]

    report = RootCauseAnalyzer.evaluate_telemetry(50, trajectory)
    assert report["flawed_pipeline_dropout_count"] > 0
    assert report["fixed_pipeline_dropout_count"] == 0
    assert report["dropout_reduction_percentage"] == 100.0
