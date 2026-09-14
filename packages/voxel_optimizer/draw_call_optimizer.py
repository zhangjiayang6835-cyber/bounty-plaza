"""Draw call batching and GPU pipeline performance modeling for voxel rendering."""

import math
from typing import List, Sequence
from packages.voxel_optimizer.models import RenderMetrics
from packages.voxel_optimizer.unified_spawner import UnifiedVoxelEntity


class DrawCallOptimizer:
    """Models GPU state switches, draw calls, and frame rate metrics."""

    def __init__(
        self,
        max_entities_per_batch: int = 2048,
        base_frame_time_ms: float = 4.0,
        draw_call_cost_ms: float = 0.75,
        geometry_overhead_ms: float = 0.01,
    ) -> None:
        """Initialize draw call optimizer with graphics pipeline constants.

        :param max_entities_per_batch: Max entities combined into one GPU draw call.
        :param base_frame_time_ms: Non-rendering baseline frame time in milliseconds.
        :param draw_call_cost_ms: Cost per individual GPU draw call in milliseconds.
        :param geometry_overhead_ms: Vertex processing overhead per block in ms.
        """
        self._max_entities_per_batch: int = max_entities_per_batch
        self._base_frame_time_ms: float = base_frame_time_ms
        self._draw_call_cost_ms: float = draw_call_cost_ms
        self._geometry_overhead_ms: float = geometry_overhead_ms

    @property
    def max_entities_per_batch(self) -> int:
        """Return maximum entity batch capacity.

        :return: Integer batch limit.
        """
        return self._max_entities_per_batch

    def evaluate_metrics(
        self, entities: Sequence[UnifiedVoxelEntity]
    ) -> RenderMetrics:
        """Compute performance metrics comparing naive vs unified architectures.

        :param entities: Sequence of active voxel entities.
        :return: RenderMetrics instance with comparative data.
        """
        total_blocks = len(entities)
        unique_types = {e.block_id for e in entities}
        unique_block_types = max(1, len(unique_types))

        naive_draw_calls = unique_block_types
        unified_draw_calls = max(
            1, math.ceil(total_blocks / self._max_entities_per_batch)
        )

        draw_call_reduction = 0.0
        if naive_draw_calls > 0:
            draw_call_reduction = max(
                0.0,
                ((naive_draw_calls - unified_draw_calls) / naive_draw_calls) * 100.0,
            )

        naive_frame_time = (
            self._base_frame_time_ms
            + (naive_draw_calls * self._draw_call_cost_ms)
            + (total_blocks * self._geometry_overhead_ms * 2.0)
        )

        unified_frame_time = (
            self._base_frame_time_ms
            + (unified_draw_calls * self._draw_call_cost_ms)
            + (total_blocks * self._geometry_overhead_ms * 0.2)
        )

        naive_fps = max(1.0, min(120.0, 1000.0 / naive_frame_time))
        unified_fps = max(1.0, min(120.0, 1000.0 / unified_frame_time))

        return RenderMetrics(
            total_blocks=total_blocks,
            unique_block_types=unique_block_types,
            naive_draw_calls=naive_draw_calls,
            unified_draw_calls=unified_draw_calls,
            draw_call_reduction_percent=draw_call_reduction,
            naive_fps=naive_fps,
            unified_fps=unified_fps,
        )

    def batch_entities(
        self, entities: Sequence[UnifiedVoxelEntity]
    ) -> List[List[UnifiedVoxelEntity]]:
        """Partition voxel entities into instanced GPU draw call batches.

        :param entities: Sequence of voxel entities to partition.
        :return: List of entity batch lists.
        """
        batches: List[List[UnifiedVoxelEntity]] = []
        chunk: List[UnifiedVoxelEntity] = []
        for entity in entities:
            chunk.append(entity)
            if len(chunk) >= self._max_entities_per_batch:
                batches.append(chunk)
                chunk = []
        if chunk:
            batches.append(chunk)
        return batches
