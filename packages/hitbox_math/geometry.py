"""Bedrock 3D geometric types and Axis-Aligned Bounding Box math.

Follows Minecraft Bedrock coordinate conventions:
+X = East,  -X = West
+Y = Up,    -Y = Down
+Z = South, -Z = North
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Vector3:
    """Immutable 3D spatial vector with vector algebra operations."""

    x: float
    y: float
    z: float

    def add(self, other: Vector3) -> Vector3:
        """Computes vector addition."""
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def subtract(self, other: Vector3) -> Vector3:
        """Computes vector subtraction."""
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def scale(self, scalar: float) -> Vector3:
        """Multiplies vector by scalar factor."""
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)

    def dot(self, other: Vector3) -> float:
        """Calculates scalar dot product."""
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vector3) -> Vector3:
        """Calculates 3D cross product."""
        cross_x = self.y * other.z - self.z * other.y
        cross_y = self.z * other.x - self.x * other.z
        cross_z = self.x * other.y - self.y * other.x
        return Vector3(cross_x, cross_y, cross_z)

    def magnitude(self) -> float:
        """Calculates Euclidean vector length."""
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def normalize(self) -> Vector3:
        """Returns unit length normalized vector."""
        mag = self.magnitude()
        if mag < 1e-9:
            return Vector3(0.0, 0.0, 0.0)
        return Vector3(self.x / mag, self.y / mag, self.z / mag)

    def distance_to(self, other: Vector3) -> float:
        """Calculates Euclidean distance to target vector."""
        return self.subtract(other).magnitude()


@dataclass(frozen=True)
class BedrockFace:
    """Cardinal bounding box face with surface outward normal."""

    name: str
    normal: Vector3


@dataclass(frozen=True)
class BoundingBox:
    """Axis-Aligned Bounding Box defined by center point and half-extents."""

    center: Vector3
    extent: Vector3

    @property
    def min_point(self) -> Vector3:
        """Calculates minimum spatial coordinates (West, Down, North)."""
        return Vector3(
            self.center.x - self.extent.x,
            self.center.y - self.extent.y,
            self.center.z - self.extent.z,
        )

    @property
    def max_point(self) -> Vector3:
        """Calculates maximum spatial coordinates (East, Up, South)."""
        return Vector3(
            self.center.x + self.extent.x,
            self.center.y + self.extent.y,
            self.center.z + self.extent.z,
        )

    def derive_vertices(self) -> tuple[Vector3, ...]:
        """Derives all eight bounding box corner vertices."""
        min_p = self.min_point
        max_p = self.max_point
        return (
            Vector3(min_p.x, min_p.y, min_p.z),
            Vector3(max_p.x, min_p.y, min_p.z),
            Vector3(min_p.x, max_p.y, min_p.z),
            Vector3(max_p.x, max_p.y, min_p.z),
            Vector3(min_p.x, min_p.y, max_p.z),
            Vector3(max_p.x, min_p.y, max_p.z),
            Vector3(min_p.x, max_p.y, max_p.z),
            Vector3(max_p.x, max_p.y, max_p.z),
        )

    def get_faces(self) -> tuple[BedrockFace, ...]:
        """Returns six cardinal faces aligned with Bedrock coordinate axes."""
        return (
            BedrockFace("East", Vector3(1.0, 0.0, 0.0)),
            BedrockFace("West", Vector3(-1.0, 0.0, 0.0)),
            BedrockFace("Up", Vector3(0.0, 1.0, 0.0)),
            BedrockFace("Down", Vector3(0.0, -1.0, 0.0)),
            BedrockFace("South", Vector3(0.0, 0.0, 1.0)),
            BedrockFace("North", Vector3(0.0, 0.0, -1.0)),
        )

    def expand(self, displacement: Vector3) -> BoundingBox:
        """Constructs expanded bounding volume enclosing swept displacement."""
        min_p = self.min_point
        max_p = self.max_point

        new_min_x = min(min_p.x, min_p.x + displacement.x)
        new_min_y = min(min_p.y, min_p.y + displacement.y)
        new_min_z = min(min_p.z, min_p.z + displacement.z)

        new_max_x = max(max_p.x, max_p.x + displacement.x)
        new_max_y = max(max_p.y, max_p.y + displacement.y)
        new_max_z = max(max_p.z, max_p.z + displacement.z)

        new_center = Vector3(
            (new_min_x + new_max_x) * 0.5,
            (new_min_y + new_max_y) * 0.5,
            (new_min_z + new_max_z) * 0.5,
        )
        new_extent = Vector3(
            (new_max_x - new_min_x) * 0.5,
            (new_max_y - new_min_y) * 0.5,
            (new_max_z - new_min_z) * 0.5,
        )
        return BoundingBox(new_center, new_extent)

    def intersects(self, other: BoundingBox) -> bool:
        """Determines static volumetric intersection against target bounding box."""
        min_a = self.min_point
        max_a = self.max_point
        min_b = other.min_point
        max_b = other.max_point

        overlap_x = min_a.x <= max_b.x and max_a.x >= min_b.x
        overlap_y = min_a.y <= max_b.y and max_a.y >= min_b.y
        overlap_z = min_a.z <= max_b.z and max_a.z >= min_b.z

        return overlap_x and overlap_y and overlap_z
