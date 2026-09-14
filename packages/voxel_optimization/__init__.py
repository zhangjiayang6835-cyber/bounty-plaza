"""Voxel optimization and draw call batching package."""

from packages.voxel_optimization.optimizer import (
    BlockMetadata,
    DrawCallOptimizer,
    FrameBudgetCalculator,
    RenderMetrics,
    TextureAtlasManager,
    VoxelBlock,
    VoxelCluster,
    evaluate_cluster_draw_calls,
)
from packages.voxel_optimization.composite_mesh import (
    ChunkBatchRenderer,
    CompositeMesh,
    CompositeMeshGenerator,
)
from packages.voxel_optimization.verifier import (
    VerificationResult,
    VoxelInvariantVerifier,
)

__all__ = [
    "BlockMetadata",
    "DrawCallOptimizer",
    "FrameBudgetCalculator",
    "RenderMetrics",
    "TextureAtlasManager",
    "VoxelBlock",
    "VoxelCluster",
    "evaluate_cluster_draw_calls",
    "ChunkBatchRenderer",
    "CompositeMesh",
    "CompositeMeshGenerator",
    "VerificationResult",
    "VoxelInvariantVerifier",
]
