"""Unit tests for Dodge Rolling and Invulnerability Frames (i-frames).
Resolves Issue #710: [BOUNTY] [MONEY] [$50] Implement Dodge Rolling.
"""

import pytest
from scripts.dodge_rolling import (
    MobActor,
    Direction,
    DamageType,
    RollConfig,
    DM_DODGE_ROLL_SPEC,
)


@pytest.fixture
def fresh_actor():
    return MobActor(name="Security Officer", x=10, y=10, health=100.0, stamina=100.0)


def test_roll_initialization_success(fresh_actor):
    """Verifies that a conscious actor with sufficient stamina initiates a roll."""
    success = fresh_actor.initiate_roll(Direction.NORTH)
    assert success is True
    assert fresh_actor.is_rolling is True
    assert fresh_actor.is_invulnerable is True
    assert fresh_actor.stamina == 75.0  # 100 - 25
    assert fresh_actor.rolling_ticks_left == 4


def test_iframe_complete_damage_invulnerability(fresh_actor):
    """Verifies that actor takes ZERO damage while executing a dodge roll."""
    # Pre-roll damage applies normally
    res_normal = fresh_actor.take_damage(20.0, DamageType.BRUTE)
    assert res_normal["applied"] == 20.0
    assert fresh_actor.health == 80.0

    # Start dodge roll
    fresh_actor.initiate_roll(Direction.EAST)
    assert fresh_actor.is_invulnerable is True

    # High-intensity attack during roll
    res_iframe = fresh_actor.take_damage(100.0, DamageType.BURN)
    assert res_iframe["applied"] == 0.0
    assert res_iframe["blocked"] == 100.0
    assert res_iframe["reason"] == "dodge_roll_iframe"
    assert fresh_actor.health == 80.0  # Health completely untouched
    assert fresh_actor.total_damage_mitigated == 100.0


def test_roll_traversal_and_expiry(fresh_actor):
    """Verifies that position advances during roll and invulnerability expires cleanly."""
    fresh_actor.initiate_roll(Direction.NORTH)
    start_y = fresh_actor.y

    # Tick 1
    fresh_actor.tick()
    assert fresh_actor.y == start_y + 1
    assert fresh_actor.is_rolling is True

    # Tick 2
    fresh_actor.tick()
    assert fresh_actor.y == start_y + 2
    assert fresh_actor.is_rolling is True

    # Tick 3
    fresh_actor.tick()
    assert fresh_actor.y == start_y + 3
    assert fresh_actor.is_rolling is True

    # Tick 4 (final roll tick)
    fresh_actor.tick()
    assert fresh_actor.y == start_y + 4
    assert fresh_actor.is_rolling is False
    assert fresh_actor.is_invulnerable is False

    # Damage applied immediately after roll must connect
    res = fresh_actor.take_damage(15.0, DamageType.BRUTE)
    assert res["applied"] == 15.0
    assert fresh_actor.health == 85.0


def test_cooldown_and_exhaustion_gating(fresh_actor):
    """Verifies that rolls cannot be chained without cooldown or during exhaustion."""
    fresh_actor.initiate_roll(Direction.SOUTH)
    # Drain roll duration
    for _ in range(4):
        fresh_actor.tick()

    # Now in cooldown window (6 ticks cooldown remaining)
    assert fresh_actor.cooldown_ticks_left > 0
    can_roll, reason = fresh_actor.can_roll(RollConfig())
    assert can_roll is False
    assert "cooldown" in reason

    # Attempting to force roll fails
    assert fresh_actor.initiate_roll(Direction.SOUTH) is False

    # Advance past cooldown
    for _ in range(fresh_actor.cooldown_ticks_left):
        fresh_actor.tick()

    assert fresh_actor.cooldown_ticks_left == 0

    # Exhaust stamina
    fresh_actor.stamina = 10.0
    can_roll_stam, reason_stam = fresh_actor.can_roll(RollConfig())
    assert can_roll_stam is False
    assert "Insufficient stamina" in reason_stam


def test_stun_and_cuff_inhibition(fresh_actor):
    """Verifies that stunned or handcuffed actors cannot roll."""
    fresh_actor.is_stunned = True
    assert fresh_actor.initiate_roll(Direction.WEST) is False

    fresh_actor.is_stunned = False
    fresh_actor.is_cuffed = True
    assert fresh_actor.initiate_roll(Direction.WEST) is False


def test_dm_specification_export():
    """Verifies that BYOND / DM source specification contains expected status effect and damage hook."""
    assert "/datum/status_effect/dodge_roll" in DM_DODGE_ROLL_SPEC
    assert "has_status_effect(/datum/status_effect/dodge_roll)" in DM_DODGE_ROLL_SPEC
    assert "adjustStamina(-25)" in DM_DODGE_ROLL_SPEC
