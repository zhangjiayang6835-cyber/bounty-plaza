"""Pytest verification suite for Issue #1209: Dynamic Voxel Display Entity Optimization."""

import json
from pathlib import Path
from packages.voxel_optimizer.models import Vector3D, AtlasCoordinate, RenderMetrics
from packages.voxel_optimizer.atlas_manager import TextureAtlasManager
from packages.voxel_optimizer.unified_spawner import (
    UnifiedVoxelEntity,
    UnifiedVoxelSpawner,
)
from packages.voxel_optimizer.draw_call_optimizer import DrawCallOptimizer
from packages.voxel_optimizer.performance_benchmarker import PerformanceBenchmarker


def test_vector3d_distance_and_dict():
    """Verify Vector3D distance calculation and dictionary serialization."""
    v1 = Vector3D(0.0, 0.0, 0.0)
    v2 = Vector3D(3.0, 4.0, 0.0)
    assert v1.distance_to(v2) == 5.0
    data = v1.to_dict()
    assert data["x"] == 0.0
    assert data["y"] == 0.0
    assert data["z"] == 0.0


def test_atlas_coordinate_serialization():
    """Verify AtlasCoordinate model bounds and dictionary serialization."""
    coord = AtlasCoordinate(0, 0.0, 0.0, 0.015625, 0.015625)
    data = coord.to_dict()
    assert data["atlas_index"] == 0
    assert data["u_min"] == 0.0
    assert data["u_max"] == 0.015625


def test_render_metrics_properties():
    """Verify RenderMetrics property calculations and dictionary conversion."""
    metrics = RenderMetrics(
        total_blocks=120,
        unique_block_types=60,
        naive_draw_calls=60,
        unified_draw_calls=1,
        draw_call_reduction_percent=98.33,
        naive_fps=18.5,
        unified_fps=118.0,
    )
    assert metrics.fps_improvement_factor == 6.38
    serialized = metrics.to_dict()
    assert serialized["fps_improvement_factor"] == 6.38
    assert serialized["draw_call_reduction_percent"] == 98.33


def test_atlas_manager_deterministic_slotting():
    """Verify TextureAtlasManager assigns identical deterministic slots on repeat calls."""
    manager = TextureAtlasManager(grid_dimension=64)
    slot1 = manager.get_atlas_index("minecraft:stone")
    slot2 = manager.get_atlas_index("minecraft:stone")
    assert slot1 == slot2
    assert manager.capacity == 4096
    assert manager.registered_count >= 16


def test_atlas_manager_novel_block_registration():
    """Verify dynamic registration of novel namespaced block types with valid UV bounds."""
    manager = TextureAtlasManager(grid_dimension=64)
    coord = manager.register_block("custom_contraption:gearbox_casing")
    assert coord.atlas_index >= 16
    assert 0.0 <= coord.u_min < coord.u_max <= 1.0
    assert 0.0 <= coord.v_min < coord.v_max <= 1.0
    lookup = manager.get_coordinate("custom_contraption:gearbox_casing")
    assert lookup is not None
    assert lookup.atlas_index == coord.atlas_index


def test_unified_entity_type_identifier():
    """Verify single unified entity type identifier across diverse block types."""
    manager = TextureAtlasManager()
    blocks = [
        "minecraft:stone",
        "minecraft:iron_block",
        "minecraft:gold_block",
        "modded:void_crystal",
    ]
    for idx, block_id in enumerate(blocks):
        entity = UnifiedVoxelEntity(
            entity_id=f"voxel_{idx}",
            location=Vector3D(float(idx), 64.0, 0.0),
            block_id=block_id,
            atlas_manager=manager,
        )
        assert entity.type_identifier == "contraption:unified_voxel_display"
        assert entity.block_id == block_id
        assert entity.is_active is True


def test_unified_entity_dynamic_properties():
    """Verify Bedrock dynamic property state generation."""
    manager = TextureAtlasManager()
    entity = UnifiedVoxelEntity(
        entity_id="voxel_alpha",
        location=Vector3D(10.0, 70.0, 15.0),
        block_id="minecraft:diamond_block",
        atlas_manager=manager,
        cluster_id="ruin_cluster_1",
    )
    props = entity.get_dynamic_properties()
    assert props["contraption:block_id"] == "minecraft:diamond_block"
    assert props["contraption:cluster_id"] == "ruin_cluster_1"
    assert isinstance(props["contraption:atlas_index"], int)


def test_runtime_block_type_mutation():
    """Verify O(1) runtime block type modification preserves entity identity."""
    manager = TextureAtlasManager()
    entity = UnifiedVoxelEntity(
        entity_id="voxel_mutable",
        location=Vector3D(5.0, 65.0, 5.0),
        block_id="minecraft:stone",
        atlas_manager=manager,
    )
    initial_id = entity.entity_id
    initial_slot = entity.atlas_index

    entity.set_block_type("minecraft:obsidian")
    assert entity.entity_id == initial_id
    assert entity.block_id == "minecraft:obsidian"
    assert entity.atlas_index != initial_slot

    props = entity.get_dynamic_properties()
    assert props["contraption:block_id"] == "minecraft:obsidian"
    assert props["contraption:atlas_index"] == entity.atlas_index


def test_spawner_cluster_tracking():
    """Verify UnifiedVoxelSpawner tracks and organizes entities by cluster ID."""
    spawner = UnifiedVoxelSpawner()
    e1 = spawner.spawn_cluster_block(
        Vector3D(0.0, 0.0, 0.0), "minecraft:stone", "cluster_a"
    )
    e2 = spawner.spawn_cluster_block(
        Vector3D(1.0, 0.0, 0.0), "minecraft:dirt", "cluster_a"
    )
    e3 = spawner.spawn_cluster_block(
        Vector3D(0.0, 1.0, 0.0), "minecraft:glass", "cluster_b"
    )

    cluster_a = spawner.get_cluster_entities("cluster_a")
    cluster_b = spawner.get_cluster_entities("cluster_b")
    assert len(cluster_a) == 2
    assert len(cluster_b) == 1
    assert e1 in cluster_a
    assert e2 in cluster_a
    assert e3 in cluster_b


def test_spawner_cluster_cleanup():
    """Verify cluster cleanup deactivates entities and clears cluster registry."""
    spawner = UnifiedVoxelSpawner()
    spawner.spawn_cluster_block(
        Vector3D(0.0, 0.0, 0.0), "minecraft:stone", "temporary_cluster"
    )
    spawner.spawn_cluster_block(
        Vector3D(1.0, 0.0, 0.0), "minecraft:dirt", "temporary_cluster"
    )

    removed_count = spawner.remove_cluster("temporary_cluster")
    assert removed_count == 2
    assert len(spawner.get_cluster_entities("temporary_cluster")) == 0


def test_draw_call_reduction_target_issue_60_blocks():
    """Verify 60+ block types scenario reduces draw calls by >= 95%."""
    spawner = UnifiedVoxelSpawner()
    optimizer = DrawCallOptimizer(max_entities_per_batch=2048)

    entities = []
    for i in range(120):
        block_id = f"contraption:type_{i % 60}"
        entity = spawner.spawn_cluster_block(
            Vector3D(float(i), 64.0, 0.0), block_id, "benchmark"
        )
        entities.append(entity)

    metrics = optimizer.evaluate_metrics(entities)
    assert metrics.total_blocks == 120
    assert metrics.unique_block_types == 60
    assert metrics.naive_draw_calls == 60
    assert metrics.unified_draw_calls == 1
    assert metrics.draw_call_reduction_percent >= 95.0


def test_client_fps_restoration_from_regression():
    """Verify FPS improves from <= 20 FPS back to >= 110 FPS on 60+ block cluster."""
    spawner = UnifiedVoxelSpawner()
    optimizer = DrawCallOptimizer(max_entities_per_batch=2048)

    entities = []
    for i in range(120):
        block_id = f"contraption:variant_{i % 60}"
        entity = spawner.spawn_cluster_block(
            Vector3D(float(i), 64.0, 0.0), block_id, "ruin"
        )
        entities.append(entity)

    metrics = optimizer.evaluate_metrics(entities)
    assert metrics.naive_fps <= 20.0
    assert metrics.unified_fps >= 110.0
    assert metrics.fps_improvement_factor >= 5.0


def test_batch_entities_partitioning():
    """Verify GPU entity batching conforms to batch size limits."""
    spawner = UnifiedVoxelSpawner()
    optimizer = DrawCallOptimizer(max_entities_per_batch=50)

    entities = []
    for i in range(125):
        entity = spawner.spawn_cluster_block(
            Vector3D(float(i), 64.0, 0.0), "minecraft:stone", "batch_test"
        )
        entities.append(entity)

    batches = optimizer.batch_entities(entities)
    assert len(batches) == 3
    assert len(batches[0]) == 50
    assert len(batches[1]) == 50
    assert len(batches[2]) == 25


def test_performance_benchmarker_sweep():
    """Verify PerformanceBenchmarker runs sweep across variable block counts."""
    optimizer = DrawCallOptimizer(max_entities_per_batch=2048)
    benchmarker = PerformanceBenchmarker(optimizer)
    suite = benchmarker.run_benchmark_suite([10, 30, 60], blocks_per_cluster=100)

    assert len(suite["test_cases"]) == 3
    for case in suite["test_cases"]:
        assert case["metrics"]["unified_draw_calls"] == 1
        assert case["metrics"]["unified_fps"] >= 100.0

    target = suite["target_case_60_types"]
    assert target["unique_block_types"] == 60
    assert target["draw_call_reduction_percent"] >= 95.0


def test_behavior_pack_entity_definition_file():
    """Verify Behavior Pack entity definition JSON structure and properties."""
    path = Path("packs/behavior_pack/entities/unified_voxel_display.json")
    assert path.exists()
    content = json.loads(path.read_text(encoding="utf-8"))
    description = content["minecraft:entity"]["description"]
    assert description["identifier"] == "contraption:unified_voxel_display"
    props = description["properties"]
    assert "contraption:block_id" in props
    assert "contraption:atlas_index" in props
    assert "contraption:cluster_id" in props


def test_resource_pack_client_entity_definition_file():
    """Verify Resource Pack client entity JSON configuration."""
    path = Path("packs/resource_pack/entity/unified_voxel_display.entity.json")
    assert path.exists()
    content = json.loads(path.read_text(encoding="utf-8"))
    client = content["minecraft:client_entity"]["description"]
    assert client["identifier"] == "contraption:unified_voxel_display"
    assert "geometry.contraption.voxel_cube" in client["geometry"]["default"]
    assert "controller.render.unified_voxel" in client["render_controllers"]


def test_resource_pack_render_controller_file():
    """Verify Resource Pack render controller JSON animation and texture setup."""
    path = Path(
        "packs/resource_pack/render_controllers/unified_voxel.render_controllers.json"
    )
    assert path.exists()
    content = json.loads(path.read_text(encoding="utf-8"))
    rc = content["render_controllers"]["controller.render.unified_voxel"]
    assert rc["geometry"] == "Geometry.default"
    assert rc["textures"] == ["Texture.atlas"]
    assert "uv_anim" in rc


def test_resource_pack_geometry_file():
    """Verify Resource Pack voxel cube geometry definition."""
    path = Path("packs/resource_pack/models/entity/voxel_cube.geo.json")
    assert path.exists()
    content = json.loads(path.read_text(encoding="utf-8"))
    geo = content["minecraft:geometry"][0]
    assert geo["description"]["identifier"] == "geometry.contraption.voxel_cube"
    cubes = geo["bones"][0]["cubes"][0]
    assert cubes["size"] == [16, 16, 16]
