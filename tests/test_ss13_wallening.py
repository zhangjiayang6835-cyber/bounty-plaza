"""Unit test suite for SS13 Wallening 3/4-Perspective & Split-Vis Subsystem.
Verifies tall wall construction, North-facing wallmount offset and layer elevation fixes,
32x40 pixel bounding box click routing and tool interaction (welding/crowbar),
split-vis alpha transparency when actors stand behind the elevated wall cap,
DMM map definitions, and DreamMaker syntax exports.
Resolves Issue #621 ($1,500 USD).
"""

import pytest
from scripts.ss13_wallening_engine import (
    SS13WalleningEngine,
    WallPerspectiveFacing,
    WallInteractionTool,
    TallWallTile,
    WallmountAttachment
)


@pytest.fixture
def wallening_engine():
    engine = SS13WalleningEngine()
    engine.construct_tall_wall((10, 10, 1), material="reinforced_plasteel", facing=WallPerspectiveFacing.SOUTH)
    return engine


def test_tall_wall_construction_and_bounding_box(wallening_engine):
    wall = wallening_engine.walls_registry[(10, 10, 1)]
    assert wall.tile_coord == (10, 10, 1)
    assert wall.material == "reinforced_plasteel"
    assert wall.wall_height_pixels == 40
    assert wall.click_bounding_box == (0, 0, 32, 40)
    assert wall.durability == 200.0


def test_north_facing_wallmount_offset_fix(wallening_engine):
    # Test mounting North-facing fixture (original revert bug where N mounts broke/occluded)
    res_north = wallening_engine.mount_wall_fixture(
        coord=(10, 10, 1),
        attachment_id="poster_security",
        name="Security Recruitment Poster",
        item_type="poster",
        facing=WallPerspectiveFacing.NORTH
    )

    assert res_north["success"] is True
    assert res_north["facing"] == WallPerspectiveFacing.NORTH.value
    # Fixed offset lifts mount to +26 Y and 4.25 layer to avoid top-cap clipping
    assert res_north["pixel_offset"] == (0, 26)
    assert res_north["render_layer"] == 4.25

    # Test East-facing fixture
    res_east = wallening_engine.mount_wall_fixture(
        coord=(10, 10, 1),
        attachment_id="apc_breaker",
        name="Main Power APC",
        item_type="apc",
        facing=WallPerspectiveFacing.EAST
    )
    assert res_east["pixel_offset"] == (24, 12)
    assert res_east["render_layer"] == 4.15


def test_click_routing_and_tool_interactions(wallening_engine):
    # Click within bounding box with Welder
    res_weld = wallening_engine.process_wall_click(
        coord=(10, 10, 1),
        click_pixel_x=16,
        click_pixel_y=35,  # Clicking upper elevated cap
        tool_used=WallInteractionTool.WELDER
    )
    assert res_weld["success"] is True
    assert res_weld["target"] == "TALL_WALL_BODY"
    assert res_weld["action"] == "WELD_OR_REPAIR_SEAM"

    # Click outside 32x40 bounding box should be rejected
    res_oob = wallening_engine.process_wall_click(
        coord=(10, 10, 1),
        click_pixel_x=35,  # x > 32
        click_pixel_y=20,
        tool_used=WallInteractionTool.WELDER
    )
    assert res_oob["success"] is False
    assert res_oob["reason"] == "CLICK_OUTSIDE_TALL_WALL_BOUNDING_BOX"

    # Click with Crowbar to pry wall
    res_crowbar = wallening_engine.process_wall_click(
        coord=(10, 10, 1),
        click_pixel_x=16,
        click_pixel_y=16,
        tool_used=WallInteractionTool.CROWBAR
    )
    assert res_crowbar["success"] is True
    assert res_crowbar["action"] == "PRY_OUTER_SHEATHING"
    assert res_crowbar["current_durability"] == 150.0  # 200 - 50


def test_fixture_direct_click_resolution(wallening_engine):
    # Mount fixture at North face (+26 Y)
    wallening_engine.mount_wall_fixture(
        coord=(10, 10, 1),
        attachment_id="fire_alarm_main",
        name="Fire Alarm Pull Station",
        item_type="alarm",
        facing=WallPerspectiveFacing.NORTH
    )

    # Click on the fixture location (16 + 0, 16 + 26 = 42)
    # Target center is (16, 42)
    res_fixture = wallening_engine.process_wall_click(
        coord=(10, 10, 1),
        click_pixel_x=16,
        click_pixel_y=40,  # Within 8px radius of (16, 42)
        tool_used=WallInteractionTool.BARE_HAND
    )
    assert res_fixture["success"] is True
    assert res_fixture["target"] == "WALLMOUNT_FIXTURE"
    assert res_fixture["fixture_id"] == "fire_alarm_main"


def test_split_vis_occlusion_calculation(wallening_engine):
    # Mob standing at (10, 11, 1) -> 1 tile North behind the wall
    res_behind = wallening_engine.calculate_split_vis_occlusion(
        wall_coord=(10, 10, 1),
        mob_coord=(10, 11, 1)
    )
    assert res_behind["is_behind_wall"] is True
    assert res_behind["split_vis_active"] is True
    assert res_behind["transparency_alpha"] == 0.4

    # Mob standing at (10, 9, 1) -> 1 tile South in front of wall -> opaque
    res_front = wallening_engine.calculate_split_vis_occlusion(
        wall_coord=(10, 10, 1),
        mob_coord=(10, 9, 1)
    )
    assert res_front["is_behind_wall"] is False
    assert res_front["split_vis_active"] is False
    assert res_front["transparency_alpha"] == 1.0


def test_dmm_map_and_dreammaker_exports(wallening_engine):
    dmm_dict = wallening_engine.export_map_integration_dmm()
    assert "IceBoxStation.dmm" in dmm_dict
    assert "/turf/closed/wall/tall/reinforced" in dmm_dict["IceBoxStation.dmm"]
    assert "pixel_y = 26" in dmm_dict["IceBoxStation.dmm"]

    dm_code = wallening_engine.export_dreammaker_code()
    assert "/turf/closed/wall/tall" in dm_code
    assert "update_split_vis" in dm_code
    assert "/obj/structure/wallmount/tall" in dm_code
