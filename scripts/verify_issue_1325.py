#!/usr/bin/env python3
"""Verification script for Issue #1325 dynamic voxel display entity optimization."""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from packages.voxel_optimization.composite_mesh import (
    ChunkBatchRenderer,
    CompositeMeshGenerator,
)
from packages.voxel_optimization.optimizer import (
    TextureAtlasManager,
    VoxelCluster,
    evaluate_cluster_draw_calls,
)
from packages.voxel_optimization.verifier import VoxelInvariantVerifier


def run_benchmark() -> bool:
    """Executes full architectural verification benchmark across 128+ voxels.

    Returns:
        True if all invariants pass, False otherwise.
    """
    atlas = TextureAtlasManager(grid_size=64)
    cluster = VoxelCluster(cluster_id="verification_cluster")

    block_types = [f"mod:sample_block_{i}" for i in range(32)]
    for i in range(256):
        b_type = block_types[i % len(block_types)]
        cluster.add_block(i % 16, (i // 16) % 16, i // 256, b_type, atlas)

    result = VoxelInvariantVerifier.verify_all_invariants(
        cluster, atlas, profile="pocket"
    )

    metrics = evaluate_cluster_draw_calls(cluster, profile="pocket")
    mesh = CompositeMeshGenerator.generate_mesh(cluster)
    reports = ChunkBatchRenderer.evaluate_cluster_chunks(cluster)

    print("=" * 60)
    print("VOXEL DISPLAY ENTITY OPTIMIZATION VERIFICATION (ISSUE #1325)")
    print("=" * 60)
    print(f"Total Voxel Blocks: {metrics.total_blocks}")
    print(f"Unique Block Types: {metrics.unique_block_types}")
    print(f"Naive Draw Calls: {metrics.naive_draw_calls}")
    print(f"Unified Draw Calls: {metrics.unified_draw_calls}")
    print(f"Draw Call Reduction: {metrics.draw_call_reduction_percent}%")
    print(f"Naive Frame Time: {metrics.naive_frame_time_ms} ms (FPS: {metrics.naive_fps})")
    print(f"Unified Frame Time: {metrics.unified_frame_time_ms} ms (FPS: {metrics.unified_fps})")
    print(f"FPS Improvement Factor: {metrics.fps_improvement_factor}x")
    print(f"Generated Mesh Vertices: {mesh.vertex_count}")
    print(f"Generated Mesh Quads: {mesh.quad_count}")
    print(f"Visible Faces: {mesh.visible_faces}, Culled Faces: {mesh.culled_faces}")
    print(f"Face Culling Efficiency: {mesh.culling_efficiency_percent}%")
    print(f"Chunks Evaluated: {len(reports)}")
    for rep in reports:
        print(
            f"  Chunk {rep.chunk_coordinate}: {rep.voxel_count} voxels | "
            f"Legacy Entities: {rep.naive_entity_count} (Exceeded: {rep.threshold_exceeded_naive}) | "
            f"Unified Entities: {rep.unified_entity_count} (Exceeded: {rep.threshold_exceeded_unified})"
        )
    print("-" * 60)
    if result.is_valid:
        print("STATUS: ALL INVARIANTS SATISFIED (TRUE VERIFICATION CONFIRMED)")
        return True

    print(f"STATUS: FAILED ({result.violation_count} violations)")
    for v in result.violations:
        print(f"  - {v}")
    return False


if __name__ == "__main__":
    success = run_benchmark()
    sys.exit(0 if success else 1)
