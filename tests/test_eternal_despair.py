"""Unit and gameplay simulation tests for Eternal Despair & Sprint Tripping mechanics.
Resolves Issue #676: [BOUNTY] [$200] [OPIRE] Bring Eternal Despair to the Players.
"""

import pytest
from scripts.eternal_despair import (
    HumanMob,
    DespairConfig,
    ItemSlot,
    DESPAIR_MESSAGES,
    DM_ETERNAL_DESPAIR_SPEC,
)


@pytest.fixture
def fresh_mob():
    return HumanMob(name="Test Assistant")


def test_walking_never_trips(fresh_mob):
    """Verifies that while not sprinting (normal walking), the actor never trips."""
    fresh_mob.toggle_sprint(False)
    # Take 50 steps walking
    for _ in range(50):
        res = fresh_mob.step_move(1, 0)
        assert res["moved"] is True
        assert res["tripped"] is False

    assert fresh_mob.is_knocked_down is False
    assert fresh_mob.total_trips_experienced == 0
    assert fresh_mob.health == 100.0


def test_sprint_tripping_drops_items_and_knocks_down(fresh_mob):
    """Verifies that sprint tripping forces knockdown, item drops, and physical damage."""
    fresh_mob.toggle_sprint(True)
    # Force 100% trip rate for deterministic test
    forced_config = DespairConfig(trip_chance_while_sprinting=1.0, trip_knockdown_seconds=3.0)

    # Actor holds toolbox and ID
    assert fresh_mob.active_hand is not None
    assert fresh_mob.inactive_hand is not None

    res = fresh_mob.step_move(1, 0, config=forced_config, rng_seed=42)

    assert res["moved"] is False
    assert res["tripped"] is True
    assert res["knockdown_applied"] == 3.0
    assert res["damage_taken"] == 5.0

    # Mob state assertions
    assert fresh_mob.is_knocked_down is True
    assert fresh_mob.health == 95.0
    assert fresh_mob.stamina == 80.0
    assert fresh_mob.sanity_mood < 100.0

    # Both items must be forcefully dropped onto the floor
    assert fresh_mob.active_hand is None
    assert fresh_mob.inactive_hand is None
    assert len(fresh_mob.dropped_floor_items) == 2
    assert "Mechanical Toolbox" in res["items_scattered"]
    assert "Assistant ID" in res["items_scattered"]


def test_cannot_move_while_knocked_down(fresh_mob):
    """Verifies that a tripped actor cannot execute steps until knockdown expires."""
    forced_config = DespairConfig(trip_chance_while_sprinting=1.0, trip_knockdown_seconds=2.0)
    fresh_mob.toggle_sprint(True)
    fresh_mob.step_move(1, 0, config=forced_config)

    assert fresh_mob.is_knocked_down is True

    # Attempting to move while prone fails
    attempt = fresh_mob.step_move(1, 0)
    assert attempt["moved"] is False
    assert attempt["reason"] == "knocked_down"

    # Advance timer by 2.0s to recover
    fresh_mob.update_tick(2.0)
    assert fresh_mob.is_knocked_down is False

    # Can move again
    fresh_mob.toggle_sprint(False)
    recovery_step = fresh_mob.step_move(1, 0)
    assert recovery_step["moved"] is True


def test_existential_despair_dialogue_lore(fresh_mob):
    """Verifies that trip events sample from authentic existential despair messages."""
    forced_config = DespairConfig(trip_chance_while_sprinting=1.0)
    fresh_mob.toggle_sprint(True)
    res = fresh_mob.step_move(1, 0, config=forced_config, rng_seed=123)

    assert any(msg in res["message"] for msg in DESPAIR_MESSAGES)
    assert "sound/misc/slip.ogg" in res["sound"]


def test_dm_specification_export():
    """Verifies TGStation BYOND / DM component structure."""
    assert "/datum/component/eternal_despair" in DM_ETERNAL_DESPAIR_SPEC
    assert "COMSIG_MOVABLE_MOVED" in DM_ETERNAL_DESPAIR_SPEC
    assert "MOVE_INTENT_RUN" in DM_ETERNAL_DESPAIR_SPEC
    assert "drop_all_held_items()" in DM_ETERNAL_DESPAIR_SPEC
    assert "Knockdown(" in DM_ETERNAL_DESPAIR_SPEC
