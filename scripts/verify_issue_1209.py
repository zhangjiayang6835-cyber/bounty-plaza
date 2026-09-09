#!/usr/bin/env python3
"""Verification script for Issue #1209 dynamic voxel entity optimization."""

import sys
from pathlib import Path
from typing import List
from packages.voxel_optimizer.models import Vector3D, RenderMetrics
from packages.voxel_optimizer.unified_spawner import (
    UnifiedVoxelEntity,
    UnifiedVoxelSpawner,
)
from packages.voxel_optimizer.draw_call_optimizer import DrawCallOptimizer
from packages.voxel_optimizer.performance_benchmarker import PerformanceBenchmarker


def _verify_entity_identities_and_mutation(
    entities: List[UnifiedVoxelEntity],
) -> bool:
    """Verify that all entities use the unified identifier and mutate in-place.

    :param entities: List of spawned UnifiedVoxelEntity instances.
    :return: True if all identity and mutation checks pass.
    """
    for entity in entities:
        if entity.type_identifier != "contraption:unified_voxel_display":
            sys.stderr.write("Verification failed: Entity identifier not unified\n")
            return False

    first_entity = entities[0]
    initial_id = first_entity.entity_id
    initial_atlas_slot = first_entity.atlas_index
    first_entity.set_block_type("minecraft:crying_obsidian")

    if first_entity.entity_id != initial_id:
        sys.stderr.write("Verification failed: Entity identity changed on update\n")
        return False

    if first_entity.atlas_index == initial_atlas_slot:
        sys.stderr.write("Verification failed: Atlas slot not updated on mutation\n")
        return False

    return True


def _verify_rendering_metrics(metrics: RenderMetrics) -> bool:
    """Verify draw call reduction and frame rate recovery thresholds.

    :param metrics: Computed RenderMetrics instance.
    :return: True if all performance thresholds are satisfied.
    """
    if metrics.naive_draw_calls != 60 or metrics.unified_draw_calls != 1:
        sys.stderr.write("Verification failed: Draw calls mismatch\n")
        return False

    if metrics.draw_call_reduction_percent < 95.0 or metrics.unified_fps < 110.0:
        sys.stderr.write("Verification failed: Performance targets not met\n")
        return False

    return True


def _verify_pack_definitions() -> bool:
    """Verify that Bedrock resource and behavior pack definitions exist.

    :return: True if all required pack files are present on disk.
    """
    pack_files = [
        "packs/behavior_pack/entities/unified_voxel_display.json",
        "packs/resource_pack/entity/unified_voxel_display.entity.json",
        "packs/resource_pack/render_controllers/unified_voxel.render_controllers.json",
        "packs/resource_pack/models/entity/voxel_cube.geo.json",
    ]
    for rel_path in pack_files:
        if not Path(rel_path).exists():
            sys.stderr.write(f"Verification failed: Missing pack file {rel_path}\n")
            return False
    return True


def run_verification() -> bool:
    """Execute end-to-end verification of unified voxel display entities.

    :return: True if all architectural constraints and benchmarks pass.
    """
    spawner = UnifiedVoxelSpawner()
    optimizer = DrawCallOptimizer(max_entities_per_batch=2048)

    entities = []
    for i in range(120):
        block_id = f"contraption:ruin_type_{i % 60}"
        loc = Vector3D(float(i % 10), float((i // 10) % 10), float(i // 100))
        entity = spawner.spawn_cluster_block(loc, block_id, "ruin_cluster")
        entities.append(entity)

    metrics = optimizer.evaluate_metrics(entities)
    if not _verify_rendering_metrics(metrics):
        return False

    if not _verify_entity_identities_and_mutation(entities):
        return False

    if not _verify_pack_definitions():
        return False

    benchmarker = PerformanceBenchmarker(optimizer)
    suite = benchmarker.run_benchmark_suite([10, 30, 60], blocks_per_cluster=120)
    if len(suite["test_cases"]) != 3:
        sys.stderr.write("Verification failed: Benchmark suite incomplete\n")
        return False

    sys.stdout.write("==================================================\n")
    sys.stdout.write("DYNAMIC VOXEL OPTIMIZATION VERIFICATION: PASSED\n")
    sys.stdout.write(f"  Total blocks evaluated: {metrics.total_blocks}\n")
    sys.stdout.write(f"  Unique block types: {metrics.unique_block_types}\n")
    sys.stdout.write(f"  Naive draw calls: {metrics.naive_draw_calls}\n")
    sys.stdout.write(f"  Unified draw calls: {metrics.unified_draw_calls}\n")
    sys.stdout.write(f"  Draw call reduction: {metrics.draw_call_reduction_percent}%\n")
    sys.stdout.write(f"  Simulated naive FPS: {metrics.naive_fps}\n")
    sys.stdout.write(f"  Simulated unified FPS: {metrics.unified_fps}\n")
    sys.stdout.write(f"  FPS improvement factor: {metrics.fps_improvement_factor}x\n")
    sys.stdout.write("==================================================\n")
    return True


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
