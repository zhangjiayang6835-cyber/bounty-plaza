"""Unit tests for DeltaStation and MetaStation DMM Map Fusion Engine.
Resolves Issue #626: [BOUNTY] [$337] Mapping bounty.
Upstream Reference: Iamgoofball/-tg-station#109.
"""

import pytest
from scripts.delta_meta_map_fusion import (
    DeltaMetaMapFusionEngine,
    DMMMap,
    DMMTileDefinition,
)


@pytest.fixture
def fusion_engine():
    return DeltaMetaMapFusionEngine(map_width=40, map_height=40)


def test_mock_map_generation(fusion_engine):
    meta = fusion_engine.create_mock_metastation()
    delta = fusion_engine.create_mock_deltastation()

    assert meta.width == 40
    assert meta.height == 40
    assert len(meta.definitions) >= 5
    assert len(meta.grid) == 40
    assert len(meta.grid[0]) == 40

    assert delta.width == 40
    assert delta.height == 40
    assert len(delta.definitions) >= 5


def test_map_fusion_north_meta_south_delta(fusion_engine):
    meta = fusion_engine.create_mock_metastation()
    delta = fusion_engine.create_mock_deltastation()

    split_y = 20
    fused = fusion_engine.fuse_maps(meta, delta, split_y=split_y)

    assert fused.width == 40
    assert fused.height == 40

    # Test North region (Y > 20) contains Meta tiles ('m...')
    for y in range(25, 40):
        for x in range(1, 39):
            key = fused.grid[y][x]
            assert key.startswith("m"), f"Expected meta tile at ({x}, {y}), got {key}"

    # Test South region (Y < 20) contains Delta tiles ('d...')
    for y in range(0, 15):
        for x in range(1, 39):
            key = fused.grid[y][x]
            assert key.startswith("d"), f"Expected delta tile at ({x}, {y}), got {key}"

    # Test Seam junction corridor at split line
    for x in range(10, 30):
        assert fused.grid[split_y][x] == "fus"


def test_dmm_serialization(fusion_engine):
    meta = fusion_engine.create_mock_metastation()
    delta = fusion_engine.create_mock_deltastation()
    fused = fusion_engine.fuse_maps(meta, delta, split_y=20)

    dmm_text = fusion_engine.serialize_to_dmm(fused)

    assert "(1,1,1) = {\"" in dmm_text
    assert '"fus" = (' in dmm_text
    assert "/area/station/hallway/central_junction" in dmm_text
    assert dmm_text.endswith("\"}")


def test_map_integrity_validation(fusion_engine):
    meta = fusion_engine.create_mock_metastation()
    delta = fusion_engine.create_mock_deltastation()
    fused = fusion_engine.fuse_maps(meta, delta, split_y=20)

    report = fusion_engine.validate_map_integrity(fused, split_y=20)

    assert report["is_valid"] is True
    assert report["total_tiles"] == 1600
    assert report["meta_north_tiles"] > 0
    assert report["delta_south_tiles"] > 0
    assert report["junction_tiles"] > 0
    assert len(report["missing_definitions"]) == 0
    assert report["status"] == "DMM_VALIDATED_SUCCESS"
