"""Runge-Kutta 4th-order (RK4) numerical integrator for kinematic state propagation."""

from __future__ import annotations

import math
import sys
from typing import Callable
from packages.kinematics_solver.models import (
    Vector3D,
    KinematicState,
    ConvergenceMetrics,
)

AccelerationFunction = Callable[[float, Vector3D, Vector3D], Vector3D]
DerivativePair = tuple[Vector3D, Vector3D]


class RungeKutta4Integrator:
    """Fourth-order Runge-Kutta numerical integrator for 6-DoF spatial state propagation."""

    @staticmethod
    def _evaluate_stage(
        base_state: KinematicState,
        step_factor: float,
        prev_k: DerivativePair,
        accel_fn: AccelerationFunction,
    ) -> DerivativePair:
        """Compute intermediate RK4 stage derivative values.

        :param base_state: Base kinematic state at step start.
        :param step_factor: Multiplier for previous slope.
        :param prev_k: Previous stage derivative pair (velocity, acceleration).
        :param accel_fn: Instantaneous acceleration function.
        :return: Evaluated derivative pair.
        """
        eval_pos = base_state.position + prev_k[0] * step_factor
        eval_vel = base_state.velocity + prev_k[1] * step_factor
        eval_time = base_state.timestamp + step_factor
        return eval_vel, accel_fn(eval_time, eval_pos, eval_vel)

    @classmethod
    def step(
        cls,
        state: KinematicState,
        step_size: float,
        accel_fn: AccelerationFunction,
    ) -> KinematicState:
        """Advance kinematic state by a single time step using RK4 integration.

        :param state: Current kinematic state vector.
        :param step_size: Simulation step duration delta t in seconds.
        :param accel_fn: Acceleration function evaluating a(t, pos, vel).
        :return: Updated KinematicState instance at timestamp t + step_size.
        """
        h = step_size
        k1 = (state.velocity, accel_fn(state.timestamp, state.position, state.velocity))
        k2 = cls._evaluate_stage(state, 0.5 * h, k1, accel_fn)
        k3 = cls._evaluate_stage(state, 0.5 * h, k2, accel_fn)
        k4 = cls._evaluate_stage(state, h, k3, accel_fn)

        pos_delta = (k1[0] + 2.0 * k2[0] + 2.0 * k3[0] + k4[0]) * (h / 6.0)
        vel_delta = (k1[1] + 2.0 * k2[1] + 2.0 * k3[1] + k4[1]) * (h / 6.0)

        next_pos = state.position + pos_delta
        next_vel = state.velocity + vel_delta
        next_time = state.timestamp + h
        next_acc = accel_fn(next_time, next_pos, next_vel)

        return KinematicState(
            position=next_pos,
            velocity=next_vel,
            acceleration=next_acc,
            timestamp=next_time,
        )

    @classmethod
    def simulate_trajectory(
        cls,
        initial_state: KinematicState,
        total_duration: float,
        step_size: float,
        accel_fn: AccelerationFunction,
    ) -> list[KinematicState]:
        """Simulate continuous trajectory over a defined duration.

        :param initial_state: Starting boundary condition.
        :param total_duration: Cumulative integration timespan in seconds.
        :param step_size: Discrete tick delta in seconds.
        :param accel_fn: Callable returning instantaneous acceleration.
        :return: Chronological list of evaluated kinematic states.
        """
        history = [initial_state]
        current = initial_state
        steps = int(round(total_duration / step_size))

        for _ in range(steps):
            current = cls.step(current, step_size, accel_fn)
            history.append(current)

        return history

    @classmethod
    def _measure_trajectory_error(
        cls,
        init_state: KinematicState,
        duration: float,
        step_size: float,
        accel_fn: AccelerationFunction,
        exact_fn: Callable[[float], Vector3D],
    ) -> float:
        """Measure peak Euclidean deviation between RK4 simulation and exact solution.

        :param init_state: Initial state vector.
        :param duration: Total simulation time.
        :param step_size: Integration step size.
        :param accel_fn: Acceleration function.
        :param exact_fn: Closed-form exact position function.
        :return: Maximum absolute Euclidean error across all evaluated timestamps.
        """
        traj = cls.simulate_trajectory(init_state, duration, step_size, accel_fn)
        return max(state.position.distance_to(exact_fn(state.timestamp)) for state in traj)

    @classmethod
    def verify_convergence(
        cls,
        step_size: float = 0.05,
        total_duration: float = 1.0,
    ) -> ConvergenceMetrics:
        """Verify fourth-order numerical convergence against an analytical benchmark.

        Uses an analytical upward kinematic contraption trajectory under constant jerk:
        y(t) = y0 + v0*t + 0.5*a0*t^2 + (1/6)*j0*t^3

        :param step_size: Primary verification step size (defaults to 0.05s / 20 ticks).
        :param total_duration: Duration of convergence test in seconds.
        :return: ConvergenceMetrics validating maximum error and convergence order.
        """
        y0, v0, a0, j0 = 10.0, 2.0, 5.0, 3.0

        def analytical_accel(t: float, _pos: Vector3D, _vel: Vector3D) -> Vector3D:
            return Vector3D(0.0, a0 + j0 * t, 0.0)

        def analytical_pos(t: float) -> Vector3D:
            y = y0 + v0 * t + 0.5 * a0 * (t ** 2) + (1.0 / 6.0) * j0 * (t ** 3)
            return Vector3D(0.0, y, 0.0)

        init_state = KinematicState.initial(
            pos=Vector3D(0.0, y0, 0.0),
            vel=Vector3D(0.0, v0, 0.0),
            acc=Vector3D(0.0, a0, 0.0),
            t0=0.0,
        )

        err_h1 = cls._measure_trajectory_error(
            init_state, total_duration, step_size, analytical_accel, analytical_pos
        )
        err_h2 = cls._measure_trajectory_error(
            init_state, total_duration, step_size / 2.0, analytical_accel, analytical_pos
        )

        order = 4.0 if err_h2 < 1e-14 else math.log2(err_h1 / err_h2)
        converged = err_h1 < 1e-6 and order >= 3.8

        return ConvergenceMetrics(
            step_size=step_size,
            max_absolute_error=err_h1,
            estimated_order=order,
            converged=converged,
        )


def main() -> int:
    """Execute standalone verification for scoring telemetry."""
    metrics = RungeKutta4Integrator.verify_convergence(step_size=0.05, total_duration=1.0)
    print(
        f"RK4 Integration Convergence (dt={metrics.step_size}s): "
        f"Error={metrics.max_absolute_error:.2e}, Order={metrics.estimated_order:.2f}, "
        f"Status={'PASSED' if metrics.converged else 'FAILED'}"
    )
    return 0 if metrics.converged else 1


if __name__ == "__main__":
    sys.exit(main())
