"""Predictive Kalman filter for 6-DoF kinematic state estimation and sub-tick extrapolation."""

from __future__ import annotations

from packages.kinematics_solver.models import Vector3D, KinematicState


class KinematicKalmanFilter:
    """Discrete-time 6-state Kalman filter estimating 3D position and velocity."""

    def __init__(
        self,
        initial_position: Vector3D,
        initial_velocity: Vector3D = Vector3D(0.0, 0.0, 0.0),
        process_noise_std: float = 0.1,
        measurement_noise_std: float = 0.05,
    ) -> None:
        """Initialize the Kalman filter with starting state and covariance parameters.

        :param initial_position: Starting spatial location vector.
        :param initial_velocity: Starting linear velocity vector.
        :param process_noise_std: Standard deviation of process noise.
        :param measurement_noise_std: Standard deviation of position sensor noise.
        """
        self._state = [
            initial_position.x,
            initial_position.y,
            initial_position.z,
            initial_velocity.x,
            initial_velocity.y,
            initial_velocity.z,
        ]

        self._p = [[0.0] * 6 for _ in range(6)]
        for i in range(3):
            self._p[i][i] = measurement_noise_std ** 2
            self._p[i + 3][i + 3] = (measurement_noise_std * 2.0) ** 2

        self._q_var = process_noise_std ** 2
        self._r_var = measurement_noise_std ** 2
        self._current_time = 0.0

    @property
    def position(self) -> Vector3D:
        """Retrieve estimated 3D position vector."""
        return Vector3D(self._state[0], self._state[1], self._state[2])

    @property
    def velocity(self) -> Vector3D:
        """Retrieve estimated 3D linear velocity vector."""
        return Vector3D(self._state[3], self._state[4], self._state[5])

    def predict(self, dt: float, control_accel: Vector3D = Vector3D(0.0, 0.0, 0.0)) -> None:
        """Execute Kalman prediction step forward by dt seconds.

        :param dt: Time interval delta in seconds.
        :param control_accel: Commanded acceleration vector.
        """
        dt2 = 0.5 * dt * dt
        self._state[0] += self._state[3] * dt + control_accel.x * dt2
        self._state[1] += self._state[4] * dt + control_accel.y * dt2
        self._state[2] += self._state[5] * dt + control_accel.z * dt2
        self._state[3] += control_accel.x * dt
        self._state[4] += control_accel.y * dt
        self._state[5] += control_accel.z * dt

        f_mat = [[1.0 if i == j else 0.0 for j in range(6)] for i in range(6)]
        f_mat[0][3] = dt
        f_mat[1][4] = dt
        f_mat[2][5] = dt

        fp = [[0.0] * 6 for _ in range(6)]
        for i in range(6):
            for j in range(6):
                fp[i][j] = sum(f_mat[i][k] * self._p[k][j] for k in range(6))

        for i in range(6):
            for j in range(6):
                self._p[i][j] = sum(fp[i][k] * f_mat[j][k] for k in range(6))

        for i in range(3):
            self._p[i][i] += self._q_var * (dt ** 4) / 4.0
            self._p[i + 3][i + 3] += self._q_var * (dt ** 2)

        self._current_time += dt

    def update(self, measurement: Vector3D) -> None:
        """Execute Kalman correction update incorporating position observation.

        :param measurement: Observed position vector z.
        """
        z = [measurement.x, measurement.y, measurement.z]
        innovations = [z[i] - self._state[i] for i in range(3)]

        s_mat = [
            self._p[0][0] + self._r_var,
            self._p[1][1] + self._r_var,
            self._p[2][2] + self._r_var,
        ]

        kalman_gain = [[0.0] * 3 for _ in range(6)]
        for i in range(6):
            for j in range(3):
                kalman_gain[i][j] = self._p[i][j] / s_mat[j]

        for i in range(6):
            correction = sum(kalman_gain[i][j] * innovations[j] for j in range(3))
            self._state[i] += correction

        new_p = [[self._p[i][j] for j in range(6)] for i in range(6)]
        for i in range(6):
            for j in range(6):
                reduction = sum(kalman_gain[i][k] * self._p[k][j] for k in range(3))
                new_p[i][j] -= reduction

        self._p = new_p

    def extrapolate(self, forward_dt: float) -> Vector3D:
        """Extrapolate forward position for sub-tick packet interpolation.

        :param forward_dt: Future time offset in seconds.
        :return: Extrapolated 3D position vector.
        """
        return Vector3D(
            self._state[0] + self._state[3] * forward_dt,
            self._state[1] + self._state[4] * forward_dt,
            self._state[2] + self._state[5] * forward_dt,
        )

    def current_state(self) -> KinematicState:
        """Retrieve current kinematic state snapshot.

        :return: KinematicState representing position, velocity, and timestamp.
        """
        return KinematicState(
            position=self.position,
            velocity=self.velocity,
            acceleration=Vector3D(0.0, 0.0, 0.0),
            timestamp=self._current_time,
        )
