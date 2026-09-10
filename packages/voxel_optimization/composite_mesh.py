"""Composite mesh generation and chunk batch rendering.

Implements directional face culling, in-world 3D primitive geometry synthesis,
and chunk-level entity budget enforcement.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple
from packages.voxel_optimization.optimizer import VoxelBlock, VoxelCluster


@dataclass(frozen=True)
class MeshBounds:
    """Bounding box coordinates for a composite mesh.

    Attributes:
        min_x: Minimum X coordinate.
        min_y: Minimum Y coordinate.
        min_z: Minimum Z coordinate.
        max_x: Maximum X coordinate.
        max_y: Maximum Y coordinate.
        max_z: Maximum Z coordinate.
    """

    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float


@dataclass(frozen=True)
class CompositeMesh:
    """3D in-world primitive geometry representation synthesized from voxel clusters.

    Attributes:
        vertex_count: Total generated vertices.
        quad_count: Total rendered face quads.
        visible_faces: Count of exterior visible faces.
        culled_faces: Count of internal occluded faces culled.
        bounds: Axis-aligned bounding box coordinates.
    """

    vertex_count: int
    quad_count: int
    visible_faces: int
    culled_faces: int
    bounds: MeshBounds

    @property
    def culling_efficiency_percent(self) -> float:
        """Percentage of total potential faces culled."""
        total_faces = self.visible_faces + self.culled_faces
        if total_faces == 0:
            return 0.0
        return round((float(self.culled_faces) / float(total_faces)) * 100.0, 2)


class CompositeMeshGenerator:
    """Synthesizes unified 3D primitive geometry with directional face culling."""

    DIRECTIONS: Tuple[Tuple[int, int, int], ...] = (
        (1, 0, 0),
        (-1, 0, 0),
        (0, 1, 0),
        (0, -1, 0),
        (0, 0, 1),
        (0, 0, -1),
    )

    @classmethod
    def _compute_bounds(cls, occupied: Set[Tuple[int, int, int]]) -> MeshBounds:
        """Calculates bounding box of occupied voxels."""
        xs = [pos[0] for pos in occupied]
        ys = [pos[1] for pos in occupied]
        zs = [pos[2] for pos in occupied]
        return MeshBounds(
            min_x=float(min(xs)),
            min_y=float(min(ys)),
            min_z=float(min(zs)),
            max_x=float(max(xs) + 1),
            max_y=float(max(ys) + 1),
            max_z=float(max(zs) + 1),
        )

    @classmethod
    def _count_faces(cls, occupied: Set[Tuple[int, int, int]]) -> Tuple[int, int]:
        """Calculates visible and culled faces using neighbor adjacency."""
        visible = 0
        culled = 0
        for pos in occupied:
            x_pos, y_pos, z_pos = pos
            for dx, dy, dz in cls.DIRECTIONS:
                neighbor = (x_pos + dx, y_pos + dy, z_pos + dz)
                if neighbor in occupied:
                    culled += 1
                else:
                    visible += 1
        return visible, culled

    @classmethod
    def generate_mesh(cls, cluster: VoxelCluster) -> CompositeMesh:
        """Generates culled composite mesh representation from a voxel cluster.

        Args:
            cluster: Populated VoxelCluster instance.

        Returns:
            CompositeMesh geometry metadata.
        """
        blocks = cluster.get_all_blocks()
        if not blocks:
            empty_bounds = MeshBounds(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
            return CompositeMesh(0, 0, 0, 0, empty_bounds)

        occupied: Set[Tuple[int, int, int]] = {b.position for b in blocks}
        bounds = cls._compute_bounds(occupied)
        visible_faces, culled_faces = cls._count_faces(occupied)

        return CompositeMesh(
            vertex_count=visible_faces * 4,
            quad_count=visible_faces,
            visible_faces=visible_faces,
            culled_faces=culled_faces,
            bounds=bounds,
        )

    @classmethod
    def calculate_culling_efficiency(cls, cluster: VoxelCluster) -> float:
        """Calculates percentage of faces eliminated via internal culling.

        Args:
            cluster: Populated VoxelCluster instance.

        Returns:
            Percentage float rounded to two decimal places.
        """
        mesh = cls.generate_mesh(cluster)
        return mesh.culling_efficiency_percent


@dataclass(frozen=True)
class ChunkRenderReport:
    """Report detailing chunk entity counts and batch threshold compliance.

    Attributes:
        chunk_coordinate: Cartesian chunk grid coordinates (chunk_x, chunk_z).
        voxel_count: Total voxels occupying this chunk.
        naive_entity_count: Armor stand entity count under legacy architecture.
        unified_entity_count: Composite entities spawned under unified architecture.
        threshold_exceeded_naive: Whether legacy architecture exceeds threshold (128).
        threshold_exceeded_unified: Whether unified architecture exceeds threshold (128).
    """

    chunk_coordinate: Tuple[int, int]
    voxel_count: int
    naive_entity_count: int
    unified_entity_count: int
    threshold_exceeded_naive: bool
    threshold_exceeded_unified: bool


class ChunkBatchRenderer:
    """Evaluates chunk entity thresholds and decupled rendering architecture."""

    MAX_CHUNK_ENTITY_THRESHOLD: int = 128

    @classmethod
    def evaluate_cluster_chunks(cls, cluster: VoxelCluster) -> List[ChunkRenderReport]:
        """Evaluates entity counts per chunk comparing legacy vs unified design.

        Args:
            cluster: VoxelCluster instance.

        Returns:
            List of ChunkRenderReport entries for each affected chunk.
        """
        distribution = cluster.blocks_per_chunk()
        reports: List[ChunkRenderReport] = []

        for coord, count in sorted(distribution.items()):
            naive_entities = count
            unified_entities = max(1, math.ceil(float(count) / 2048.0))

            exceeded_naive = naive_entities > cls.MAX_CHUNK_ENTITY_THRESHOLD
            exceeded_unified = unified_entities > cls.MAX_CHUNK_ENTITY_THRESHOLD

            report = ChunkRenderReport(
                chunk_coordinate=coord,
                voxel_count=count,
                naive_entity_count=naive_entities,
                unified_entity_count=unified_entities,
                threshold_exceeded_naive=exceeded_naive,
                threshold_exceeded_unified=exceeded_unified,
            )
            reports.append(report)

        return reports

    @classmethod
    def group_blocks_by_chunk(
        cls, blocks: List[VoxelBlock]
    ) -> Dict[Tuple[int, int], List[VoxelBlock]]:
        """Groups a list of blocks into sublists keyed by chunk coordinate.

        Args:
            blocks: List of VoxelBlock entries.

        Returns:
            Dictionary mapping chunk coordinate to block list.
        """
        grouped: Dict[Tuple[int, int], List[VoxelBlock]] = {}
        for block in blocks:
            coord = block.chunk_coordinate
            if coord not in grouped:
                grouped[coord] = []
            grouped[coord].append(block)
        return grouped
