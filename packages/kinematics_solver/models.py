"""Kinematic and spatial models for numerical integration and collision verification."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Vector3D:
    """Immutable three-dimensional Euclidean vector.

    :param x: X-coordinate component.
    :param y: Y-coordinate component.
    :param z: Z-coordinate component.
    """

    x: float
    y: float
    z: float

    def __add__(self, other: Vector3D) -> Vector3D:
        """Add two vectors component-wise.

        :param other: Vector to add.
        :return: Resulting sum vector.
        """
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vector3D) -> Vector3D:
        """Subtract another vector component-wise.

        :param other: Vector to subtract.
        :return: Resulting difference vector.
        """
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> Vector3D:
        """Multiply vector by a scalar value.

        :param scalar: Numerical scale factor.
        :return: Scaled vector.
        """
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> Vector3D:
        """Multiply vector by a scalar value on left.

        :param scalar: Numerical scale factor.
        :return: Scaled vector.
        """
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> Vector3D:
        """Divide vector by a non-zero scalar value.

        :param scalar: Numerical divisor.
        :return: Divided vector.
        """
        if abs(scalar) < 1e-12:
            raise ZeroDivisionError("Vector division by near-zero scalar.")
        return Vector3D(self.x / scalar, self.y / scalar, self.z / scalar)

    def dot(self, other: Vector3D) -> float:
        """Compute inner dot product with another vector.

        :param other: Vector to dot with.
        :return: Scalar dot product.
        """
        return self.x * other.x + self.y * other.y + self.z * other.z

    def norm(self) -> float:
        """Calculate Euclidean magnitude of vector.

        :return: Vector magnitude.
        """
        return math.sqrt(self.dot(self))

    def distance_to(self, other: Vector3D) -> float:
        """Calculate Euclidean distance to another point vector.

        :param other: Target point vector.
        :return: Distance between vectors.
        """
        return (self - other).norm()

    def to_dict(self) -> dict[str, float]:
        """Convert vector components to serializable dictionary.

        :return: Dictionary containing x, y, and z floats.
        """
        return {"x": self.x, "y": self.y, "z": self.z}

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> Vector3D:
        """Construct vector from dictionary mapping.

        :param data: Dictionary containing x, y, z keys.
        :return: Vector3D instance.
        """
        return cls(float(data["x"]), float(data["y"]), float(data["z"]))


@dataclass(frozen=True)
class KinematicState:
    """State vector representing instantaneous position, velocity, and acceleration.

    :param position: Current spatial position vector.
    :param velocity: Current linear velocity vector.
    :param acceleration: Current acceleration vector.
    :param timestamp: Temporal simulation marker in seconds.
    """

    position: Vector3D
    velocity: Vector3D
    acceleration: Vector3D
    timestamp: float

    @classmethod
    def initial(
        cls,
        pos: Vector3D,
        vel: Vector3D = Vector3D(0.0, 0.0, 0.0),
        acc: Vector3D = Vector3D(0.0, 0.0, 0.0),
        t0: float = 0.0,
    ) -> KinematicState:
        """Create an initial kinematic state.

        :param pos: Initial position.
        :param vel: Initial velocity.
        :param acc: Initial acceleration.
        :param t0: Starting time.
        :return: New KinematicState instance.
        """
        return cls(position=pos, velocity=vel, acceleration=acc, timestamp=t0)


@dataclass(frozen=True)
class ColliderBox:
    """Axis-Aligned Bounding Box (AABB) for spatial collision resolution.

    :param min_point: Minimum coordinate boundary vector.
    :param max_point: Maximum coordinate boundary vector.
    """

    min_point: Vector3D
    max_point: Vector3D

    def contains(self, point: Vector3D) -> bool:
        """Determine whether a given point lies within the bounding volume.

        :param point: Vector point to test.
        :return: True if enclosed within bounds.
        """
        return (
            self.min_point.x <= point.x <= self.max_point.x
            and self.min_point.y <= point.y <= self.max_point.y
            and self.min_point.z <= point.z <= self.max_point.z
        )

    def intersects(self, other: ColliderBox) -> bool:
        """Determine whether this box overlaps with another bounding volume.

        :param other: Other collider box to test against.
        :return: True if volumes intersect.
        """
        return (
            self.min_point.x <= other.max_point.x
            and self.max_point.x >= other.min_point.x
            and self.min_point.y <= other.max_point.y
            and self.max_point.y >= other.min_point.y
            and self.min_point.z <= other.max_point.z
            and self.max_point.z >= other.min_point.z
        )

    def top_face_y(self) -> float:
        """Retrieve maximum vertical coordinate representing the supportive top face.

        :return: Top face Y coordinate.
        """
        return self.max_point.y

    def vertical_clearance(self, player_feet_y: float) -> float:
        """Calculate vertical signed separation between player feet and box top face.

        :param player_feet_y: Vertical elevation of player base.
        :return: Signed elevation difference.
        """
        return player_feet_y - self.top_face_y()


@dataclass(frozen=True)
class CollisionResult:
    """Outcome report for collision detection pass.

    :param has_collision: Flag indicating boundary overlap or surface contact.
    :param separation_distance: Vertical separation to support plane.
    :param normal: Surface normal reaction vector.
    :param is_supported: Flag indicating player is resting securely on top face.
    """

    has_collision: bool
    separation_distance: float
    normal: Vector3D
    is_supported: bool


@dataclass(frozen=True)
class ConvergenceMetrics:
    """Convergence validation metrics for numerical integrators.

    :param step_size: Integration time step delta.
    :param max_absolute_error: Maximum deviation from analytical solution.
    :param estimated_order: Empirical convergence order exponent.
    :param converged: Verification flag against tolerance thresholds.
    """

    step_size: float
    max_absolute_error: float
    estimated_order: float
    converged: bool
