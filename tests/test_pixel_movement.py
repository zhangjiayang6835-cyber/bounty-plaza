"""Unit and integration test suite for BYOND pixel movement and sub-tile kinematics.
Resolves Issue #628: [BOUNTY] [$100] [AGENTIC / AI] Implement pixel movement.
"""

import pytest
from scripts.pixel_movement import (
    PixelMob,
    BoundingBox,
    Direction,
    TILE_SIZE_PX,
    BYOND_PIXEL_MOVEMENT_DM_SOURCE,
)


@pytest.fixture
def player():
    return PixelMob(
        mob_id="mob_human_1",
        name="Engineer Jack",
        tile_x=2,
        tile_y=2,
        step_x=0.0,
        step_y=0.0,
        step_size=8.0,
    )


def test_pixel_movement_sub_tile_steps(player):
    """Verifies that each step moves the mob by step_size pixels within the tile."""
    assert player.global_px_x == 64.0  # 2 * 32
    assert player.global_px_y == 64.0  # 2 * 32

    # Step EAST (8 pixels)
    res = player.move_pixel(Direction.EAST, obstacles=[])
    assert res["success"] is True
    assert player.step_x == 8.0
    assert player.tile_x == 2
    assert player.global_px_x == 72.0

    # Three more steps EAST -> 8*3 = 24 pixels -> total 32 pixels -> crosses tile boundary to tile_x = 3
    player.move_pixel(Direction.EAST, obstacles=[])
    player.move_pixel(Direction.EAST, obstacles=[])
    res4 = player.move_pixel(Direction.EAST, obstacles=[])

    assert res4["success"] is True
    assert player.tile_x == 3
    assert player.step_x == 0.0
    assert player.global_px_x == 96.0  # 3 * 32


def test_obstacle_collision_blocks_movement(player):
    """Verifies that bounding box collision with dense obstacles prevents movement."""
    # Place wall obstacle at px_y = 112 (player bbox top starts at 94)
    wall = BoundingBox(px_x=64.0, px_y=112.0, width=32.0, height=32.0)

    # Move North towards the wall
    # Initial bbox top is 64 + 2 + 28 = 94.
    # Step 1 North by 8 -> top 102 < 112, clears
    res1 = player.move_pixel(Direction.NORTH, obstacles=[wall])
    assert res1["success"] is True

    # Step 2 North by 8 -> top 110 < 112, clears
    res2 = player.move_pixel(Direction.NORTH, obstacles=[wall])
    assert res2["success"] is True

    # Step 3 North by 8 -> top 118 > 112 -> intersects wall bottom (112) -> collides!
    res3 = player.move_pixel(Direction.NORTH, obstacles=[wall])
    assert res3["success"] is False
    assert res3["blocked_by"] == "obstacle"


def test_friendly_mob_swapping(player):
    """Verifies that two unencumbered friendly mobs swap positions when traversing narrow spaces."""
    other_mob = PixelMob(
        mob_id="mob_human_2",
        name="Scientist Maria",
        tile_x=2,
        tile_y=3,
        step_x=0.0,
        step_y=0.0,
    )

    orig_player_pos = (player.tile_x, player.tile_y)
    orig_other_pos = (other_mob.tile_x, other_mob.tile_y)

    # Move player North directly into Maria
    # Step moves player towards other mob's bounding box
    res = player.move_pixel(Direction.NORTH, obstacles=[], other_mobs=[other_mob])

    assert res["success"] is True
    assert res["swapped_with"] == "mob_human_2"
    assert (player.tile_x, player.tile_y) == orig_other_pos
    assert (other_mob.tile_x, other_mob.tile_y) == orig_player_pos


def test_pulling_tether_kinematics(player):
    """Verifies that pulled mobs follow behind when distance exceeds tether radius."""
    pulled_mob = PixelMob(
        mob_id="mob_human_3",
        name="Injured Assistant",
        tile_x=1,
        tile_y=2,
    )
    player.start_pulling(pulled_mob)

    # Move player multiple steps away to trigger tether follow
    for _ in range(5):
        player.move_pixel(Direction.EAST, obstacles=[])

    # Pulled mob should have updated position following player's trail
    dist = abs(player.global_px_x - pulled_mob.global_px_x)
    assert dist <= 32.0, "Pulled mob must stay within 1 tile tether distance"

    player.stop_pulling()
    assert player.pulling is None
    assert pulled_mob.pulled_by is None


def test_byond_dm_pixel_movement_syntax():
    """Verifies BYOND DM configuration matches engine specifications."""
    assert "movement_mode = PIXEL_MOVEMENT" in BYOND_PIXEL_MOVEMENT_DM_SOURCE
    assert "step_size = 8" in BYOND_PIXEL_MOVEMENT_DM_SOURCE
    assert "bound_width = 28" in BYOND_PIXEL_MOVEMENT_DM_SOURCE
    assert "Cross(atom/movable/mover)" in BYOND_PIXEL_MOVEMENT_DM_SOURCE
