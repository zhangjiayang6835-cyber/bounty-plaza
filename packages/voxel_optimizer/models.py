"""Data models and immutable value representations for voxel optimization."""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class Vector3D:
    """Three-dimensional Cartesian coordinate vector."""

    x: float
    y: float
    z: float

    def distance_to(self, other: "Vector3D") -> float:
        """Calculate Euclidean distance between two spatial vectors.

        :param other: Target Vector3D coordinate.
        :return: Floating point Euclidean distance.
        """
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return (dx * dx + dy * dy + dz * dz) ** 0.5

    def to_dict(self) -> Dict[str, float]:
        """Convert vector to a plain dictionary representation.

        :return: Dictionary containing x, y, and z coordinates.
        """
        return {"x": self.x, "y": self.y, "z": self.z}


@dataclass(frozen=True)
class AtlasCoordinate:
    """Texture atlas UV coordinate boundaries and slot index."""

    atlas_index: int
    u_min: float
    v_min: float
    u_max: float
    v_max: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert UV coordinate to dictionary format.

        :return: Dictionary with index and UV limits.
        """
        return {
            "atlas_index": self.atlas_index,
            "u_min": round(self.u_min, 6),
            "v_min": round(self.v_min, 6),
            "u_max": round(self.u_max, 6),
            "v_max": round(self.v_max, 6),
        }


@dataclass(frozen=True)
class RenderMetrics:
    """Quantitative performance metrics comparing naive and unified rendering architectures."""

    total_blocks: int
    unique_block_types: int
    naive_draw_calls: int
    unified_draw_calls: int
    draw_call_reduction_percent: float
    naive_fps: float
    unified_fps: float

    @property
    def fps_improvement_factor(self) -> float:
        """Calculate relative frame rate improvement factor.

        :return: Multiplier indicating relative performance improvement.
        """
        if self.naive_fps <= 0:
            return 1.0
        return round(self.unified_fps / self.naive_fps, 2)

    def to_dict(self) -> Dict[str, Any]:
        """Convert render metrics to serializable dictionary.

        :return: Dictionary of evaluation metrics.
        """
        return {
            "total_blocks": self.total_blocks,
            "unique_block_types": self.unique_block_types,
            "naive_draw_calls": self.naive_draw_calls,
            "unified_draw_calls": self.unified_draw_calls,
            "draw_call_reduction_percent": round(self.draw_call_reduction_percent, 2),
            "naive_fps": round(self.naive_fps, 2),
            "unified_fps": round(self.unified_fps, 2),
            "fps_improvement_factor": self.fps_improvement_factor,
        }
