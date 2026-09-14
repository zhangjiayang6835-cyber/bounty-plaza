"""Test suite for Issue #1325: Dynamic voxel display entity optimization.

Verifies draw call reduction, texture atlas UV mapping, composite mesh generation,
face culling efficiency, chunk entity threshold compliance, and frame budget limits.
"""

import pytest
from packages.voxel_optimization.composite_mesh import (
    ChunkBatchRenderer,
    CompositeMeshGenerator,
)
from packages.voxel_optimization.optimizer import (
    DrawCallOptimizer,
    FrameBudgetCalculator,
    TextureAtlasManager,
    VoxelCluster,
    evaluate_cluster_draw_calls,
)
from packages.voxel_optimization.verifier import VoxelInvariantVerifier


class TestTextureAtlasManager:
    """Test suite for texture atlas registry and UV mapping."""

    def test_deterministic_indexing(self) -> None:
        """Tests that identical block identifiers return the same atlas index."""
        manager = TextureAtlasManager(grid_size=64)
        idx1 = manager.get_atlas_index("minecraft:stone")
        idx2 = manager.get_atlas_index("minecraft:stone")
        assert idx1 == idx2

    def test_distinct_block_indices(self) -> None:
        """Tests that different block types receive unique atlas indices."""
        manager = TextureAtlasManager(grid_size=64)
        idx_stone = manager.get_atlas_index("minecraft:stone")
        idx_dirt = manager.get_atlas_index("minecraft:dirt")
        assert idx_stone != idx_dirt

    def test_uv_coordinate_validity(self) -> None:
        """Tests that registered block UV coordinates form valid bounding boxes."""
        manager = TextureAtlasManager(grid_size=64)
        meta = manager.register_block("custom:test_block")
        assert meta.u_min < meta.u_max
        assert meta.v_min < meta.v_max
        assert 0.0 <= meta.u_min <= 1.0
        assert 0.0 <= meta.u_max <= 1.0
        assert 0.0 <= meta.v_min <= 1.0
        assert 0.0 <= meta.v_max <= 1.0

    def test_capacity_overflow(self) -> None:
        """Tests that exceeding atlas grid capacity raises ValueError."""
        manager = TextureAtlasManager(grid_size=2, register_defaults=False)
        with pytest.raises(ValueError, match="capacity exceeded"):
            for i in range(10):
                manager.register_block(f"test:block_{i}")


class TestVoxelCluster:
    """Test suite for spatial cluster data structures and dynamic mutations."""

    def test_add_and_query_block(self) -> None:
        """Tests adding blocks and querying by coordinates."""
        atlas = TextureAtlasManager(grid_size=64)
        cluster = VoxelCluster(cluster_id="c1")
        block = cluster.add_block(10, 20, 30, "minecraft:stone", atlas)

        assert block.position == (10, 20, 30)
        assert cluster.block_count() == 1
        assert cluster.get_block(10, 20, 30) is not None
        assert cluster.get_block(0, 0, 0) is None

    def test_runtime_block_mutation(self) -> None:
        """Tests O(1) in-place block type update without cluster recreation."""
        atlas = TextureAtlasManager(grid_size=64)
        cluster = VoxelCluster(cluster_id="c1")
        cluster.add_block(5, 5, 5, "minecraft:stone", atlas)

        updated = cluster.update_block_type(5, 5, 5, "minecraft:diamond_block", atlas)
        assert updated is True
        mutated_block = cluster.get_block(5, 5, 5)
        assert mutated_block is not None
        assert mutated_block.block_id == "minecraft:diamond_block"

        non_existent = cluster.update_block_type(99, 99, 99, "minecraft:dirt", atlas)
        assert non_existent is False

    def test_remove_block(self) -> None:
        """Tests removing a block from the cluster."""
        atlas = TextureAtlasManager(grid_size=64)
        cluster = VoxelCluster(cluster_id="c1")
        cluster.add_block(1, 2, 3, "minecraft:obsidian", atlas)
        assert cluster.remove_block(1, 2, 3) is True
        assert cluster.block_count() == 0
        assert cluster.remove_block(1, 2, 3) is False

    def test_chunk_partitioning(self) -> None:
        """Tests mapping voxel positions to 16x16 chunk boundaries."""
        atlas = TextureAtlasManager(grid_size=64)
        cluster = VoxelCluster(cluster_id="multi_chunk")
        cluster.add_block(0, 64, 0, "minecraft:stone", atlas)
        cluster.add_block(15, 64, 15, "minecraft:dirt", atlas)
        cluster.add_block(16, 64, 0, "minecraft:grass_block", atlas)
        cluster.add_block(32, 64, 32, "minecraft:sand", atlas)

        chunks = cluster.chunk_coordinates()
        assert chunks == {(0, 0), (1, 0), (2, 2)}
        dist = cluster.blocks_per_chunk()
        assert dist[(0, 0)] == 2
        assert dist[(1, 0)] == 1
        assert dist[(2, 2)] == 1


class TestDrawCallOptimization:
    """Test suite for draw call reduction and frame budget preservation."""

    def test_draw_call_reduction_under_load(self) -> None:
        """Tests that 128 diverse voxels achieve over 80 percent draw call reduction."""
        atlas = TextureAtlasManager(grid_size=64)
        cluster = VoxelCluster(cluster_id="benchmark")

        block_types = [f"mod:sample_block_{i}" for i in range(64)]
        for i in range(128):
            b_type = block_types[i % len(block_types)]
            cluster.add_block(i, 64, 0, b_type, atlas)

        metrics = evaluate_cluster_draw_calls(cluster, profile="pocket")
        assert metrics.total_blocks == 128
        assert metrics.unique_block_types == 64
        assert metrics.naive_draw_calls == 64
        assert metrics.unified_draw_calls == 1
        assert metrics.draw_call_reduction_percent >= 80.0
        assert metrics.unified_fps >= 60
        assert metrics.unified_frame_time_ms < 16.67
        assert metrics.fps_improvement_factor >= 2.0

    def test_frame_budget_calculator(self) -> None:
        """Tests frame budget checking and fps calculation."""
        assert FrameBudgetCalculator.is_budget_exceeded(124.0) is True
        assert FrameBudgetCalculator.is_budget_exceeded(8.5) is False
        assert FrameBudgetCalculator.calculate_fps(8.0) == 120
        assert FrameBudgetCalculator.calculate_fps(124.0) == 8
        assert FrameBudgetCalculator.calculate_fps(0.0) == 120

    def test_batching_partition(self) -> None:
        """Tests partitioning blocks into batches adhering to max batch size."""
        optimizer = DrawCallOptimizer(max_entities_per_batch=50)
        atlas = TextureAtlasManager(grid_size=64)
        cluster = VoxelCluster()
        for i in range(125):
            cluster.add_block(i, 0, 0, "minecraft:stone", atlas)

        batches = optimizer.batch_blocks(cluster.get_all_blocks())
        assert len(batches) == 3
        assert len(batches[0]) == 50
        assert len(batches[1]) == 50
        assert len(batches[2]) == 25


class TestCompositeMeshAndCulling:
    """Test suite for 3D primitive geometry synthesis and face culling."""

    def test_solid_cube_culling(self) -> None:
        """Tests that a 3x3x3 solid voxel cube correctly culls internal faces."""
        atlas = TextureAtlasManager(grid_size=64)
        cluster = VoxelCluster()

        for x in range(3):
            for y in range(3):
                for z in range(3):
                    cluster.add_block(x, y, z, "minecraft:stone", atlas)

        mesh = CompositeMeshGenerator.generate_mesh(cluster)
        assert cluster.block_count() == 27
        assert mesh.visible_faces == 54
        assert mesh.culled_faces == 108
        assert mesh.quad_count == 54
        assert mesh.vertex_count == 216
        assert mesh.culling_efficiency_percent == 66.67

    def test_empty_cluster_mesh(self) -> None:
        """Tests generating mesh for empty cluster."""
        cluster = VoxelCluster()
        mesh = CompositeMeshGenerator.generate_mesh(cluster)
        assert mesh.vertex_count == 0
        assert mesh.quad_count == 0
        assert mesh.visible_faces == 0
        assert mesh.culled_faces == 0
        assert mesh.culling_efficiency_percent == 0.0

    def test_mesh_bounding_box(self) -> None:
        """Tests that composite mesh bounds accurately cover occupied voxels."""
        atlas = TextureAtlasManager(grid_size=64)
        cluster = VoxelCluster()
        cluster.add_block(2, 5, 7, "minecraft:stone", atlas)
        cluster.add_block(10, 15, 20, "minecraft:dirt", atlas)

        mesh = CompositeMeshGenerator.generate_mesh(cluster)
        assert mesh.bounds.min_x == 2.0
        assert mesh.bounds.min_y == 5.0
        assert mesh.bounds.min_z == 7.0
        assert mesh.bounds.max_x == 11.0
        assert mesh.bounds.max_y == 16.0
        assert mesh.bounds.max_z == 21.0


class TestChunkBatchRendererAndVerifier:
    """Test suite for chunk threshold enforcement and end-to-end verification."""

    def test_chunk_threshold_mitigation(self) -> None:
        """Tests that 200 voxels in a single chunk exceed legacy limit but pass unified."""
        atlas = TextureAtlasManager(grid_size=64)
        cluster = VoxelCluster()

        for i in range(200):
            cluster.add_block(i % 16, i // 16, 0, "minecraft:stone", atlas)

        reports = ChunkBatchRenderer.evaluate_cluster_chunks(cluster)
        assert len(reports) == 1
        rep = reports[0]
        assert rep.chunk_coordinate == (0, 0)
        assert rep.voxel_count == 200
        assert rep.naive_entity_count == 200
        assert rep.threshold_exceeded_naive is True
        assert rep.unified_entity_count == 1
        assert rep.threshold_exceeded_unified is False

    def test_invariant_verifier_success(self) -> None:
        """Tests end-to-end verification passing without violations."""
        atlas = TextureAtlasManager(grid_size=64)
        cluster = VoxelCluster()

        types = [f"mod:voxel_type_{i}" for i in range(16)]
        for i in range(128):
            cluster.add_block(i % 16, (i // 16) % 8, 0, types[i % len(types)], atlas)

        res = VoxelInvariantVerifier.verify_all_invariants(cluster, atlas, profile="pocket")
        assert res.is_valid is True
        assert res.violation_count == 0
        assert res.metrics.unified_frame_time_ms < 16.67
        assert res.metrics.unified_fps >= 60
        assert res.metrics.draw_call_reduction_percent >= 80.0
