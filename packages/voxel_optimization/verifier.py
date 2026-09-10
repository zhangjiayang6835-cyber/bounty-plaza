"""Invariant verification suite for dynamic voxel rendering systems.

Validates entity decoupling, batch render thresholds, frame budget compliance,
and texture atlas deterministic mapping.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
from packages.voxel_optimization.composite_mesh import (
    ChunkBatchRenderer,
    CompositeMesh,
    CompositeMeshGenerator,
)
from packages.voxel_optimization.optimizer import (
    FrameBudgetCalculator,
    RenderMetrics,
    TextureAtlasManager,
    VoxelCluster,
    evaluate_cluster_draw_calls,
)


@dataclass(frozen=True)
class VerificationResult:
    """Summary of all invariant verifications.

    Attributes:
        is_valid: True if all invariants passed without error.
        violations: List of invariant violation messages.
        metrics: Evaluated render metrics.
        mesh: Synthesized composite mesh metadata.
    """

    is_valid: bool
    violations: Tuple[str, ...]
    metrics: RenderMetrics
    mesh: CompositeMesh

    @property
    def violation_count(self) -> int:
        """Count of detected invariant violations."""
        return len(self.violations)


class VoxelInvariantVerifier:
    """Rigorous invariant verifier executing defensive QA on voxel architectures."""

    MAX_CHUNK_ENTITY_THRESHOLD: int = 128
    MAX_PERMISSIBLE_FRAME_TIME_MS: float = 16.67
    MIN_DRAW_CALL_REDUCTION_PERCENT: float = 80.0

    @classmethod
    def verify_chunk_entity_threshold(
        cls, cluster: VoxelCluster
    ) -> List[str]:
        """Verifies that unified chunk entity count never exceeds 128 entities.

        Args:
            cluster: VoxelCluster instance.

        Returns:
            List of violation descriptions.
        """
        violations: List[str] = []
        reports = ChunkBatchRenderer.evaluate_cluster_chunks(cluster)
        for report in reports:
            if report.threshold_exceeded_unified:
                violations.append(
                    f"Chunk {report.chunk_coordinate} exceeded entity threshold: "
                    f"{report.unified_entity_count} entities (max {cls.MAX_CHUNK_ENTITY_THRESHOLD})"
                )
        return violations

    @classmethod
    def verify_frame_budget(
        cls, metrics: RenderMetrics
    ) -> List[str]:
        """Verifies that unified frame tick remains strictly within 16.67ms budget.

        Args:
            metrics: RenderMetrics instance.

        Returns:
            List of violation descriptions.
        """
        violations: List[str] = []
        if FrameBudgetCalculator.is_budget_exceeded(metrics.unified_frame_time_ms):
            violations.append(
                f"Unified frame time {metrics.unified_frame_time_ms}ms exceeds 60 FPS "
                f"budget threshold ({cls.MAX_PERMISSIBLE_FRAME_TIME_MS}ms)"
            )
        if metrics.unified_fps < 60:
            violations.append(
                f"Unified FPS {metrics.unified_fps} dropped below 60 FPS threshold"
            )
        return violations

    @classmethod
    def verify_draw_call_reduction(
        cls, metrics: RenderMetrics
    ) -> List[str]:
        """Verifies that draw calls are reduced by at least 80 percent.

        Args:
            metrics: RenderMetrics instance.

        Returns:
            List of violation descriptions.
        """
        violations: List[str] = []
        if metrics.draw_call_reduction_percent < cls.MIN_DRAW_CALL_REDUCTION_PERCENT:
            violations.append(
                f"Draw call reduction {metrics.draw_call_reduction_percent}% is below "
                f"minimum required {cls.MIN_DRAW_CALL_REDUCTION_PERCENT}%"
            )
        return violations

    @classmethod
    def verify_atlas_determinism(
        cls, atlas_manager: TextureAtlasManager, block_ids: List[str]
    ) -> List[str]:
        """Verifies deterministic UV coordinate mapping and non-overlapping indexes.

        Args:
            atlas_manager: TextureAtlasManager instance.
            block_ids: List of block identifier strings.

        Returns:
            List of violation descriptions.
        """
        violations: List[str] = []
        seen_indices: Dict[int, str] = {}

        for block_id in block_ids:
            idx1 = atlas_manager.get_atlas_index(block_id)
            idx2 = atlas_manager.get_atlas_index(block_id)
            if idx1 != idx2:
                violations.append(
                    f"Non-deterministic atlas index resolution for {block_id}: {idx1} vs {idx2}"
                )

            if idx1 in seen_indices and seen_indices[idx1] != block_id:
                violations.append(
                    f"Atlas index collision: {block_id} and {seen_indices[idx1]} "
                    f"both mapped to {idx1}"
                )
            seen_indices[idx1] = block_id

            meta = atlas_manager.get_metadata(block_id)
            if meta is None:
                violations.append(f"Missing metadata entry for block {block_id}")
            else:
                if meta.u_min >= meta.u_max or meta.v_min >= meta.v_max:
                    violations.append(
                        f"Invalid UV bounding box coordinates for block {block_id}"
                    )

        return violations

    @classmethod
    def verify_all_invariants(
        cls,
        cluster: VoxelCluster,
        atlas_manager: TextureAtlasManager,
        profile: str = "pocket",
    ) -> VerificationResult:
        """Executes complete defensive verification across all system invariants.

        Args:
            cluster: VoxelCluster instance.
            atlas_manager: TextureAtlasManager instance.
            profile: Target hardware profile ('pocket', 'desktop', 'console').

        Returns:
            VerificationResult instance.
        """
        metrics = evaluate_cluster_draw_calls(cluster, profile=profile)
        mesh = CompositeMeshGenerator.generate_mesh(cluster)

        all_violations: List[str] = []
        all_violations.extend(cls.verify_chunk_entity_threshold(cluster))
        all_violations.extend(cls.verify_frame_budget(metrics))
        all_violations.extend(cls.verify_draw_call_reduction(metrics))

        unique_blocks = [b.block_id for b in cluster.get_all_blocks()]
        all_violations.extend(cls.verify_atlas_determinism(atlas_manager, unique_blocks))

        is_valid = len(all_violations) == 0
        return VerificationResult(
            is_valid=is_valid,
            violations=tuple(all_violations),
            metrics=metrics,
            mesh=mesh,
        )
