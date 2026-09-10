"""Geometry definitions and coordinate helpers for Minecraft Bedrock bounding boxes.

Coordinates follow Bedrock alignment:
+X = East, -X = West
+Y = Up,   -Y = Down
+Z = South, -Z = North
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Vector3:
    """Three-dimensional Cartesian vector."""

    x: float
    y: float
    z: float

    def add(self, other: "Vector3") -> "Vector3":
        """Adds another vector to this vector."""
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def subtract(self, other: "Vector3") -> "Vector3":
        """Subtracts another vector from this vector."""
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def scale(self, factor: float) -> "Vector3":
        """Scales vector by scalar factor."""
        return Vector3(self.x * factor, self.y * factor, self.z * factor)

    def dot(self, other: "Vector3") -> float:
        """Computes dot product between two vectors."""
        return self.x * other.x + self.y * other.y + self.z * other.z

    def magnitude(self) -> float:
        """Computes Euclidean length of this vector."""
        return (self.x * self.x + self.y * self.y + self.z * self.z) ** 0.5


@dataclass(frozen=True)
class BedrockFace:
    """Cardinal face definition for Bedrock bounding box."""

    name: str
    normal: Vector3
    vertices: tuple[Vector3, ...]


class BoundingBox:
    """Axis-Aligned Bounding Box conforming to Bedrock coordinate conventions."""

    def __init__(self, center: Vector3, extent: Vector3) -> None:
        """Initializes bounding box with center and half-extents."""
        ext_x = abs(extent.x)
        ext_y = abs(extent.y)
        ext_z = abs(extent.z)

        self.center = Vector3(center.x, center.y, center.z)
        self.extent = Vector3(ext_x, ext_y, ext_z)
        self.min_point = Vector3(center.x - ext_x, center.y - ext_y, center.z - ext_z)
        self.max_point = Vector3(center.x + ext_x, center.y + ext_y, center.z + ext_z)

    @classmethod
    def from_min_max(cls, min_point: Vector3, max_point: Vector3) -> "BoundingBox":
        """Constructs BoundingBox from minimum and maximum corner points."""
        min_x = min(min_point.x, max_point.x)
        min_y = min(min_point.y, max_point.y)
        min_z = min(min_point.z, max_point.z)
        max_x = max(min_point.x, max_point.x)
        max_y = max(min_point.y, max_point.y)
        max_z = max(min_point.z, max_point.z)

        center = Vector3(
            (min_x + max_x) * 0.5,
            (min_y + max_y) * 0.5,
            (min_z + max_z) * 0.5,
        )
        extent = Vector3(
            (max_x - min_x) * 0.5,
            (max_y - min_y) * 0.5,
            (max_z - min_z) * 0.5,
        )
        return cls(center, extent)

    def derive_vertices(self) -> list[Vector3]:
        """Derives 8 bounding box vertices following Bedrock conventions."""
        min_p = self.min_point
        max_p = self.max_point
        vertex_list: list[Vector3] = []
        vertex_list.append(Vector3(min_p.x, min_p.y, min_p.z))
        vertex_list.append(Vector3(max_p.x, min_p.y, min_p.z))
        vertex_list.append(Vector3(min_p.x, max_p.y, min_p.z))
        vertex_list.append(Vector3(max_p.x, max_p.y, min_p.z))
        vertex_list.append(Vector3(min_p.x, min_p.y, max_p.z))
        vertex_list.append(Vector3(max_p.x, min_p.y, max_p.z))
        vertex_list.append(Vector3(min_p.x, max_p.y, max_p.z))
        vertex_list.append(Vector3(max_p.x, max_p.y, max_p.z))
        return vertex_list

    def get_faces(self) -> list[BedrockFace]:
        """Derives 6 cardinal faces with outward Bedrock normal vectors."""
        verts = self.derive_vertices()
        faces: list[BedrockFace] = []
        faces.append(
            BedrockFace(
                name="East",
                normal=Vector3(1.0, 0.0, 0.0),
                vertices=(verts[1], verts[5], verts[7], verts[3]),
            )
        )
        faces.append(
            BedrockFace(
                name="West",
                normal=Vector3(-1.0, 0.0, 0.0),
                vertices=(verts[0], verts[2], verts[6], verts[4]),
            )
        )
        faces.append(
            BedrockFace(
                name="Up",
                normal=Vector3(0.0, 1.0, 0.0),
                vertices=(verts[2], verts[3], verts[7], verts[6]),
            )
        )
        faces.append(
            BedrockFace(
                name="Down",
                normal=Vector3(0.0, -1.0, 0.0),
                vertices=(verts[0], verts[4], verts[5], verts[1]),
            )
        )
        faces.append(
            BedrockFace(
                name="South",
                normal=Vector3(0.0, 0.0, 1.0),
                vertices=(verts[4], verts[5], verts[7], verts[6]),
            )
        )
        faces.append(
            BedrockFace(
                name="North",
                normal=Vector3(0.0, 0.0, -1.0),
                vertices=(verts[0], verts[1], verts[3], verts[2]),
            )
        )
        return faces

    def translate(self, offset: Vector3) -> "BoundingBox":
        """Translates bounding box by displacement vector."""
        return BoundingBox(self.center.add(offset), self.extent)

    def expand(self, displacement: Vector3) -> "BoundingBox":
        """Expands bounding box to enclose translation motion vector."""
        min_x = min(self.min_point.x, self.min_point.x + displacement.x)
        min_y = min(self.min_point.y, self.min_point.y + displacement.y)
        min_z = min(self.min_point.z, self.min_point.z + displacement.z)
        max_x = max(self.max_point.x, self.max_point.x + displacement.x)
        max_y = max(self.max_point.y, self.max_point.y + displacement.y)
        max_z = max(self.max_point.z, self.max_point.z + displacement.z)
        return BoundingBox.from_min_max(
            Vector3(min_x, min_y, min_z),
            Vector3(max_x, max_y, max_z),
        )

    def intersects(self, other: "BoundingBox") -> bool:
        """Determines whether two bounding boxes statically intersect."""
        return (
            self.min_point.x < other.max_point.x
            and self.max_point.x > other.min_point.x
            and self.min_point.y < other.max_point.y
            and self.max_point.y > other.min_point.y
            and self.min_point.z < other.max_point.z
            and self.max_point.z > other.min_point.z
        )
