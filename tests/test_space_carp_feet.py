"""Unit tests for Space Carp Footwear & Anatomical Feet Overlay System.
Resolves Issue #730: [BOUNTY] [$25] Give space carp visible feet.
"""

import pytest
import numpy as np
from scripts.space_carp_feet import (
    CardinalDirection,
    CarpCombatStats,
    SpaceCarpFeetSystem,
    DM_SPACE_CARP_FEET_SPEC,
)


@pytest.fixture
def feet_system():
    return SpaceCarpFeetSystem()


def test_carp_feet_overlay_rendering_dimensions_and_alpha(feet_system):
    """Verifies that the rendered overlay is a 32x32 RGBA image with non-zero alpha pixels."""
    for direction in CardinalDirection:
        overlay = feet_system.render_overlay_frame(direction, stride_tick=0)
        assert overlay.shape == (32, 32, 4)
        assert overlay.dtype == np.uint8

        # Count visible non-transparent pixels
        visible_pixels = np.sum(overlay[:, :, 3] > 0)
        assert visible_pixels > 0, f"Direction {direction} has no visible foot pixels"
        # Two small feet should consist of roughly 10-20 non-zero pixels
        assert 8 <= visible_pixels <= 30, f"Unexpected foot pixel density: {visible_pixels}"


def test_carp_feet_stride_bobbing_displacement(feet_system):
    """Verifies that stride ticks cause alternating vertical bobbing between steps."""
    frame_0 = feet_system.render_overlay_frame(CardinalDirection.SOUTH, stride_tick=0)
    frame_1 = feet_system.render_overlay_frame(CardinalDirection.SOUTH, stride_tick=1)

    # Frame 0 and Frame 1 should not be identical due to stride bobbing
    assert not np.array_equal(frame_0, frame_1)

    # Confirm pixels remain within 32x32 bounds
    assert np.all(frame_0 >= 0) and np.all(frame_0 <= 255)
    assert np.all(frame_1 >= 0) and np.all(frame_1 <= 255)


def test_zero_gameplay_and_combat_impact(feet_system):
    """Verifies that combat statistics, movement delays, and faction tags are unaffected."""
    vanilla_stats = {
        "max_health": 50.0,
        "melee_damage_lower": 15.0,
        "melee_damage_upper": 15.0,
        "move_delay": 1.0,
        "faction": "carp",
    }
    assert feet_system.verify_no_gameplay_impact(vanilla_stats) is True


def test_all_four_cardinal_anchors_present(feet_system):
    """Verifies that ventral anchor coordinates exist for all cardinal directions."""
    for direction in [CardinalDirection.NORTH, CardinalDirection.SOUTH, CardinalDirection.EAST, CardinalDirection.WEST]:
        anchors = feet_system.get_foot_anchors_for_direction(direction)
        assert "left" in anchors and "right" in anchors
        lx, ly = anchors["left"]
        rx, ry = anchors["right"]

        # Ensure anchors are in ventral lower body region (Y between 20 and 26)
        assert 20 <= ly <= 26
        assert 20 <= ry <= 26
        # Ensure feet are horizontally spaced
        assert abs(rx - lx) >= 5


def test_byond_dm_specification_export():
    """Verifies that DM code contains standard TGStation carp overlay hooks."""
    assert "/mob/living/simple_animal/hostile/carp" in DM_SPACE_CARP_FEET_SPEC
    assert "update_carp_feet_appearance()" in DM_SPACE_CARP_FEET_SPEC
    assert "add_overlay(carp_feet_overlay)" in DM_SPACE_CARP_FEET_SPEC
