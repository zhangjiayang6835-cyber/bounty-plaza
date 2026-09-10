"""Voxel rendering optimization and draw call batching engine.

Provides unified entity batching, texture atlas UV calculation,
and frame budget performance metrics for dynamic voxel structures.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class BlockMetadata:
    """Metadata definition for a voxel block registered in the atlas system.

    Attributes:
        block_id: Namespaced identifier of the block.
        texture_path: Path to the underlying texture asset.
        atlas_index: Numerical index within the texture atlas grid.
        u_min: Minimum horizontal texture coordinate.
        v_min: Minimum vertical texture coordinate.
        u_max: Maximum horizontal texture coordinate.
        v_max: Maximum vertical texture coordinate.
    """

    block_id: str
    texture_path: str
    atlas_index: int
    u_min: float
    v_min: float
    u_max: float
    v_max: float


@dataclass
class VoxelBlock:
    """Representation of an individual voxel block within a cluster.

    Attributes:
        x: X-axis Cartesian coordinate.
        y: Y-axis Cartesian coordinate.
        z: Z-axis Cartesian coordinate.
        block_id: Namespaced block identifier.
        atlas_index: Resolved atlas index.
        cluster_id: Associated cluster group identifier.
    """

    x: int
    y: int
    z: int
    block_id: str
    atlas_index: int
    cluster_id: str = "default"

    @property
    def position(self) -> Tuple[int, int, int]:
        """Cartesian coordinates tuple of the voxel."""
        return (self.x, self.y, self.z)

    @property
    def chunk_coordinate(self) -> Tuple[int, int]:
        """Calculates 16x16 chunk grid coordinates."""
        chunk_x = math.floor(self.x / 16.0)
        chunk_z = math.floor(self.z / 16.0)
        return (int(chunk_x), int(chunk_z))


@dataclass(frozen=True)
class PerformanceMetric:
    """Frame duration and framerate comparison metrics.

    Attributes:
        naive_frame_time_ms: Render frame tick duration for naive design.
        unified_frame_time_ms: Render frame tick duration for batched design.
        naive_fps: Simulated frames per second for naive approach.
        unified_fps: Simulated frames per second for unified approach.
        fps_improvement_factor: Factor of frame rate enhancement.
    """

    naive_frame_time_ms: float
    unified_frame_time_ms: float
    naive_fps: int
    unified_fps: int
    fps_improvement_factor: float


@dataclass(frozen=True)
class RenderMetrics:
    """Voxel rendering metrics comparing naive vs unified architectures.

    Attributes:
        total_blocks: Count of active voxel blocks in cluster.
        unique_block_types: Count of distinct block identifiers.
        naive_draw_calls: Required draw calls in individual entity design.
        unified_draw_calls: Required draw calls in batched architecture.
        draw_call_reduction_percent: Percentage reduction in draw calls.
        performance: PerformanceMetric containing frame times and framerates.
    """

    total_blocks: int
    unique_block_types: int
    naive_draw_calls: int
    unified_draw_calls: int
    draw_call_reduction_percent: float
    performance: PerformanceMetric

    @property
    def naive_frame_time_ms(self) -> float:
        """Frame time duration for naive rendering."""
        return self.performance.naive_frame_time_ms

    @property
    def unified_frame_time_ms(self) -> float:
        """Frame time duration for unified batched rendering."""
        return self.performance.unified_frame_time_ms

    @property
    def naive_fps(self) -> int:
        """Simulated FPS for naive rendering."""
        return self.performance.naive_fps

    @property
    def unified_fps(self) -> int:
        """Simulated FPS for unified batched rendering."""
        return self.performance.unified_fps

    @property
    def fps_improvement_factor(self) -> float:
        """Improvement ratio of unified FPS over naive FPS."""
        return self.performance.fps_improvement_factor


class TextureAtlasManager:
    """Manages unified texture atlas coordinate mapping and index resolution."""

    def __init__(self, grid_size: int = 64, register_defaults: bool = True) -> None:
        """Initializes texture atlas manager with specific grid dimensions.

        Args:
            grid_size: Number of texture cells per row and column in the atlas.
            register_defaults: Whether to register standard default block types.
        """
        self._grid_size: int = grid_size
        self._registry: Dict[str, BlockMetadata] = {}
        self._next_index: int = 0
        if register_defaults:
            self._register_default_blocks()

    @property
    def grid_size(self) -> int:
        """Grid dimension cell count."""
        return self._grid_size

    def _register_default_blocks(self) -> None:
        """Pre-populates common block types into the atlas registry."""
        defaults = (
            "minecraft:stone",
            "minecraft:dirt",
            "minecraft:grass_block",
            "minecraft:cobblestone",
            "minecraft:oak_planks",
            "minecraft:iron_block",
            "minecraft:gold_block",
            "minecraft:diamond_block",
            "minecraft:obsidian",
            "minecraft:glass",
            "minecraft:sand",
            "minecraft:gravel",
            "minecraft:bricks",
            "minecraft:mossy_cobblestone",
            "minecraft:netherrack",
            "minecraft:soul_sand",
        )
        for block_id in defaults:
            self.register_block(block_id)

    def register_block(
        self, block_id: str, custom_texture: Optional[str] = None
    ) -> BlockMetadata:
        """Registers a block type and assigns deterministic UV atlas coordinates.

        Args:
            block_id: Unique namespaced block identifier.
            custom_texture: Optional custom texture path.

        Returns:
            Metadata entry for the registered block.

        Raises:
            ValueError: If atlas capacity is exceeded.
        """
        if block_id in self._registry:
            return self._registry[block_id]

        max_capacity = self._grid_size * self._grid_size
        if self._next_index >= max_capacity:
            raise ValueError(
                f"Texture atlas capacity exceeded: maximum {max_capacity} entries."
            )

        index = self._next_index
        self._next_index += 1

        col = index % self._grid_size
        row = index // self._grid_size
        cell_size = 1.0 / float(self._grid_size)

        u_min = float(col) * cell_size
        v_min = float(row) * cell_size
        u_max = float(col + 1) * cell_size
        v_max = float(row + 1) * cell_size

        clean_name = block_id.replace(":", "_")
        texture_path = custom_texture or f"textures/blocks/{clean_name}"

        meta = BlockMetadata(
            block_id=block_id,
            texture_path=texture_path,
            atlas_index=index,
            u_min=u_min,
            v_min=v_min,
            u_max=u_max,
            v_max=v_max,
        )
        self._registry[block_id] = meta
        return meta

    def get_atlas_index(self, block_id: str) -> int:
        """Resolves the atlas index for a block identifier.

        Args:
            block_id: Namespaced block identifier.

        Returns:
            Integer atlas index.
        """
        if block_id in self._registry:
            return self._registry[block_id].atlas_index
        return self.register_block(block_id).atlas_index

    def get_metadata(self, block_id: str) -> Optional[BlockMetadata]:
        """Retrieves complete UV coordinate metadata for a block identifier.

        Args:
            block_id: Namespaced block identifier.

        Returns:
            BlockMetadata entry or None if not found.
        """
        return self._registry.get(block_id)

    def registered_count(self) -> int:
        """Returns the count of registered blocks in the atlas.

        Returns:
            Total registered block entries.
        """
        return len(self._registry)


class VoxelCluster:
    """Manages spatial aggregation and dynamic updates of voxel blocks."""

    def __init__(self, cluster_id: str = "default") -> None:
        """Initializes a voxel cluster instance.

        Args:
            cluster_id: Unique identifier of the cluster.
        """
        self._cluster_id: str = cluster_id
        self._blocks: Dict[Tuple[int, int, int], VoxelBlock] = {}

    @property
    def cluster_id(self) -> str:
        """Unique cluster identifier."""
        return self._cluster_id

    def add_block(
        self,
        x: int,
        y: int,
        z: int,
        block_id: str,
        atlas_manager: TextureAtlasManager,
    ) -> VoxelBlock:
        """Adds or updates a voxel block at specified coordinates.

        Args:
            x: Cartesian X coordinate.
            y: Cartesian Y coordinate.
            z: Cartesian Z coordinate.
            block_id: Namespaced block identifier.
            atlas_manager: Active texture atlas manager.

        Returns:
            Instantiated VoxelBlock instance.
        """
        atlas_index = atlas_manager.get_atlas_index(block_id)
        block = VoxelBlock(
            x=x,
            y=y,
            z=z,
            block_id=block_id,
            atlas_index=atlas_index,
            cluster_id=self._cluster_id,
        )
        self._blocks[(x, y, z)] = block
        return block

    def update_block_type(
        self,
        x: int,
        y: int,
        z: int,
        new_block_id: str,
        atlas_manager: TextureAtlasManager,
    ) -> bool:
        """Updates block type in O(1) time without rebuilding spatial graph.

        Args:
            x: Cartesian X coordinate.
            y: Cartesian Y coordinate.
            z: Cartesian Z coordinate.
            new_block_id: New namespaced block identifier.
            atlas_manager: Active texture atlas manager.

        Returns:
            True if block was updated, False if coordinates not found.
        """
        pos = (x, y, z)
        block = self._blocks.get(pos)
        if block is None:
            return False
        block.block_id = new_block_id
        block.atlas_index = atlas_manager.get_atlas_index(new_block_id)
        return True

    def remove_block(self, x: int, y: int, z: int) -> bool:
        """Removes a voxel block from the cluster.

        Args:
            x: Cartesian X coordinate.
            y: Cartesian Y coordinate.
            z: Cartesian Z coordinate.

        Returns:
            True if removed, False if nonexistent.
        """
        pos = (x, y, z)
        if pos in self._blocks:
            del self._blocks[pos]
            return True
        return False

    def get_block(self, x: int, y: int, z: int) -> Optional[VoxelBlock]:
        """Retrieves block at specified Cartesian coordinates.

        Args:
            x: Cartesian X coordinate.
            y: Cartesian Y coordinate.
            z: Cartesian Z coordinate.

        Returns:
            VoxelBlock instance or None.
        """
        return self._blocks.get((x, y, z))

    def get_all_blocks(self) -> List[VoxelBlock]:
        """Retrieves list of all blocks in cluster.

        Returns:
            List of VoxelBlock entries.
        """
        return list(self._blocks.values())

    def block_count(self) -> int:
        """Returns total active blocks in cluster.

        Returns:
            Block count integer.
        """
        return len(self._blocks)

    def chunk_coordinates(self) -> Set[Tuple[int, int]]:
        """Returns set of unique 16x16 chunk coordinates intersected.

        Returns:
            Set of (chunk_x, chunk_z) tuples.
        """
        coords: Set[Tuple[int, int]] = set()
        for block in self._blocks.values():
            coords.add(block.chunk_coordinate)
        return coords

    def blocks_per_chunk(self) -> Dict[Tuple[int, int], int]:
        """Calculates distribution of blocks across chunks.

        Returns:
            Mapping from (chunk_x, chunk_z) to block count.
        """
        distribution: Dict[Tuple[int, int], int] = {}
        for block in self._blocks.values():
            coord = block.chunk_coordinate
            distribution[coord] = distribution.get(coord, 0) + 1
        return distribution


class FrameBudgetCalculator:
    """Calculates render frame time budgets against target framerates."""

    TARGET_FRAME_TIME_MS: float = 16.666666666666668

    @classmethod
    def is_budget_exceeded(cls, frame_time_ms: float) -> bool:
        """Determines whether frame time exceeds 60 FPS budget.

        Args:
            frame_time_ms: Render frame duration in milliseconds.

        Returns:
            True if frame time exceeds 16.67ms, False otherwise.
        """
        return frame_time_ms > cls.TARGET_FRAME_TIME_MS

    @classmethod
    def calculate_fps(cls, frame_time_ms: float) -> int:
        """Calculates integer FPS from millisecond frame duration.

        Args:
            frame_time_ms: Duration in milliseconds.

        Returns:
            Estimated frame rate clamped between 1 and 120 FPS.
        """
        if frame_time_ms <= 0.0:
            return 120
        fps = int(1000.0 / frame_time_ms)
        return max(1, min(120, fps))


class DrawCallOptimizer:
    """Calculates draw call batching, state switch reduction, and performance."""

    def __init__(
        self,
        max_entities_per_batch: int = 2048,
        base_frame_time_ms: float = 4.0,
        draw_call_cost_ms: float = 0.75,
        geometry_overhead_ms: float = 0.01,
    ) -> None:
        """Initializes optimizer with hardware profile characteristics.

        Args:
            max_entities_per_batch: Maximum instanced count per GPU draw call.
            base_frame_time_ms: Baseline rendering pass overhead.
            draw_call_cost_ms: GPU driver overhead per draw call.
            geometry_overhead_ms: Vertex processing overhead per block.
        """
        self._max_entities_per_batch: int = max_entities_per_batch
        self._base_frame_time_ms: float = base_frame_time_ms
        self._draw_call_cost_ms: float = draw_call_cost_ms
        self._geometry_overhead_ms: float = geometry_overhead_ms

    def evaluate_metrics(self, blocks: List[VoxelBlock]) -> RenderMetrics:
        """Computes render metrics comparing naive vs unified architectures.

        Args:
            blocks: List of active voxel blocks.

        Returns:
            RenderMetrics evaluation object.
        """
        total_blocks = len(blocks)
        unique_types = {b.block_id for b in blocks}
        unique_block_types = max(1, len(unique_types))

        naive_draw_calls = unique_block_types
        unified_draw_calls = max(
            1, math.ceil(float(total_blocks) / float(self._max_entities_per_batch))
        )

        draw_call_reduction = 0.0
        if naive_draw_calls > 0:
            diff = float(naive_draw_calls - unified_draw_calls)
            draw_call_reduction = max(0.0, (diff / float(naive_draw_calls)) * 100.0)

        naive_frame_time = (
            self._base_frame_time_ms
            + float(naive_draw_calls) * self._draw_call_cost_ms
            + float(total_blocks) * self._geometry_overhead_ms * 2.0
        )

        unified_frame_time = (
            self._base_frame_time_ms
            + float(unified_draw_calls) * self._draw_call_cost_ms
            + float(total_blocks) * self._geometry_overhead_ms * 0.2
        )

        naive_fps = FrameBudgetCalculator.calculate_fps(naive_frame_time)
        unified_fps = FrameBudgetCalculator.calculate_fps(unified_frame_time)

        factor = float(unified_fps) / float(naive_fps) if naive_fps > 0 else 1.0

        perf = PerformanceMetric(
            naive_frame_time_ms=round(naive_frame_time, 2),
            unified_frame_time_ms=round(unified_frame_time, 2),
            naive_fps=naive_fps,
            unified_fps=unified_fps,
            fps_improvement_factor=round(factor, 2),
        )

        return RenderMetrics(
            total_blocks=total_blocks,
            unique_block_types=unique_block_types,
            naive_draw_calls=naive_draw_calls,
            unified_draw_calls=unified_draw_calls,
            draw_call_reduction_percent=round(draw_call_reduction, 2),
            performance=perf,
        )

    def batch_blocks(self, blocks: List[VoxelBlock]) -> List[List[VoxelBlock]]:
        """Partitions blocks into GPU submit batches.

        Args:
            blocks: List of voxel blocks.

        Returns:
            Batched list of block sub-lists.
        """
        batches: List[List[VoxelBlock]] = []
        for i in range(0, len(blocks), self._max_entities_per_batch):
            batches.append(blocks[i : i + self._max_entities_per_batch])
        return batches


def evaluate_cluster_draw_calls(
    cluster: VoxelCluster, profile: str = "pocket"
) -> RenderMetrics:
    """Evaluates cluster render metrics against designated device profile.

    Args:
        cluster: VoxelCluster instance.
        profile: Device profile ('pocket', 'desktop', 'console').

    Returns:
        RenderMetrics evaluation object.
    """
    profiles = {
        "pocket": (1024, 5.0, 0.90, 0.015),
        "desktop": (4096, 2.0, 0.30, 0.005),
        "console": (2048, 3.5, 0.50, 0.010),
    }
    config = profiles.get(profile, profiles["pocket"])
    optimizer = DrawCallOptimizer(
        max_entities_per_batch=config[0],
        base_frame_time_ms=config[1],
        draw_call_cost_ms=config[2],
        geometry_overhead_ms=config[3],
    )
    return optimizer.evaluate_metrics(cluster.get_all_blocks())


def main() -> None:
    """Executes verification benchmark and prints optimization metrics."""
    atlas = TextureAtlasManager(grid_size=64)
    cluster = VoxelCluster(cluster_id="benchmark_voxels")

    blocks = (
        "minecraft:stone",
        "minecraft:dirt",
        "minecraft:diamond_block",
        "minecraft:oak_planks",
        "minecraft:gold_block",
        "minecraft:iron_block",
        "minecraft:obsidian",
        "minecraft:glass",
    )

    for i in range(128):
        b_type = blocks[i % len(blocks)]
        cluster.add_block(i % 16, (i // 16) % 8, i // 32, b_type, atlas)

    metrics = evaluate_cluster_draw_calls(cluster, profile="pocket")
    exceeded = FrameBudgetCalculator.is_budget_exceeded(metrics.unified_frame_time_ms)
    print(f"Total Blocks: {metrics.total_blocks}")
    print(f"Unified Draw Calls: {metrics.unified_draw_calls}")
    print(f"Unified Frame Time: {metrics.unified_frame_time_ms} ms")
    print(f"Unified FPS: {metrics.unified_fps}")
    print(f"Budget Exceeded: {exceeded}")


if __name__ == "__main__":
    main()
