"""Unit and visual alignment test suite for Space Carp Visible Feet Overlay.
Resolves Issue #730: Give space carp visible feet ($25 USD).
"""

import pytest
from scripts.space_carp_feet import (
    Direction,
    SpaceCarp,
    DIRECTIONAL_FOOT_OFFSETS,
)


@pytest.fixture
def carp():
    return SpaceCarp()


def test_initial_carp_appearance_has_two_feet(carp):
    appearance = carp.render_appearance()
    assert appearance["name"] == "space carp"
    assert appearance["direction"] == "SOUTH"
    assert appearance["feet_count"] == 2
    assert len(appearance["overlays"]) == 2


def test_directional_feet_alignment_all_cardinal_directions(carp):
    for direction in [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]:
        carp.set_facing_direction(direction)
        appearance = carp.render_appearance()

        assert appearance["direction"] == direction.value
        assert len(appearance["overlays"]) == 2

        left = appearance["overlays"][0]
        right = appearance["overlays"][1]

        # Verify icon states are direction-specific
        assert direction.value.lower() in left["icon_state"]
        assert direction.value.lower() in right["icon_state"]

        # Verify pixel offsets are within reasonable bounding box (no floating or detached pixels)
        assert -16 <= left["pixel_x"] <= 16
        assert -16 <= left["pixel_y"] <= 16
        assert -16 <= right["pixel_x"] <= 16
        assert -16 <= right["pixel_y"] <= 16


def test_gameplay_statistics_are_strictly_preserved(carp):
    """Core Acceptance Criterion: Feet visual must not alter any combat, health, speed, or resistance stats."""
    assert carp.max_health == 25.0
    assert carp.health == 25.0
    assert carp.melee_damage_lower == 15
    assert carp.melee_damage_upper == 20
    assert carp.speed == 1.0
    assert carp.faction == ["carp"]
    assert carp.atmosphere_resistant is True
    assert carp.vacuum_resistant is True


def test_disabled_feet_overlay_returns_clean_base(carp):
    carp.has_feet_overlay = False
    appearance = carp.render_appearance()
    assert appearance["feet_count"] == 0
    assert appearance["overlays"] == []
