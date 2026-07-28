"""Tests for dodge rolling with invulnerability frames (issue #710)."""

import pytest

from web.dodge_roll import (
    DEFAULT_ROLL_COOLDOWN,
    DEFAULT_ROLL_DISTANCE,
    DEFAULT_ROLL_DURATION,
    LivingEntity,
    position_delta,
    resolve_direction,
)


@pytest.fixture
def entity() -> LivingEntity:
    return LivingEntity(name="tester", facing="EAST")


def test_dodge_roll_starts_and_grants_invulnerability(entity: LivingEntity):
    assert entity.dodge_roll(now=0.0) is True
    assert entity._dodge.is_rolling is True
    assert entity.is_invulnerable is True
    assert entity.has_trait("GODMODE")


def test_no_damage_while_dodge_rolling(entity: LivingEntity):
    entity.dodge_roll(direction="NORTH", now=0.0)
    taken = entity.apply_damage(50.0)
    assert taken == 0.0
    assert entity.health == 100.0


def test_damage_applies_when_not_rolling(entity: LivingEntity):
    taken = entity.apply_damage(25.0)
    assert taken == 25.0
    assert entity.health == 75.0


def test_forced_damage_bypasses_invulnerability(entity: LivingEntity):
    entity.dodge_roll(now=0.0)
    taken = entity.apply_damage(10.0, forced=True)
    assert taken == 10.0
    assert entity.health == 90.0


def test_invulnerability_ends_after_duration(entity: LivingEntity):
    entity.dodge_roll(now=1.0)
    entity.tick(now=1.0 + DEFAULT_ROLL_DURATION)
    assert entity._dodge.is_rolling is False
    assert entity.is_invulnerable is False
    taken = entity.apply_damage(15.0)
    assert taken == 15.0
    assert entity.health == 85.0


def test_cooldown_blocks_repeat_roll(entity: LivingEntity):
    assert entity.dodge_roll(now=0.0) is True
    entity.tick(now=DEFAULT_ROLL_DURATION)
    assert entity.dodge_roll(now=DEFAULT_ROLL_DURATION) is False
    # After full cooldown, roll is available again.
    ready_at = DEFAULT_ROLL_COOLDOWN
    assert entity.dodge_roll(now=ready_at) is True


def test_roll_moves_entity_in_direction(entity: LivingEntity):
    before = (entity.x, entity.y)
    entity.dodge_roll(direction="EAST", now=0.0)
    after = (entity.x, entity.y)
    assert after[0] > before[0]
    assert after[1] == before[1]
    assert position_delta(before, after) == pytest.approx(DEFAULT_ROLL_DISTANCE)


def test_cannot_roll_while_incapacitated():
    downed = LivingEntity(name="downed", standing=False)
    assert downed.dodge_roll(now=0.0) is False

    stunned = LivingEntity(name="stunned", immobilized=True)
    assert stunned.dodge_roll(now=0.0) is False

    unconscious = LivingEntity(name="ko", conscious=False)
    assert unconscious.dodge_roll(now=0.0) is False

    buckled = LivingEntity(name="buckled", buckled=True)
    assert buckled.dodge_roll(now=0.0) is False


def test_cannot_start_second_roll_while_active(entity: LivingEntity):
    assert entity.dodge_roll(direction="SOUTH", now=0.0) is True
    assert entity.dodge_roll(direction="NORTH", now=0.1) is False
    assert entity._dodge.roll_direction == "SOUTH"


def test_resolve_direction_prefers_intended():
    assert resolve_direction("EAST", intended="NORTH") == "NORTH"
    assert resolve_direction("WEST", intended=None) == "WEST"
    assert resolve_direction("bogus", intended=None) == "NORTH"


def test_state_snapshot(entity: LivingEntity):
    entity.dodge_roll(direction="WEST", now=5.0)
    state = entity._dodge.state(now=5.0)
    assert state["is_rolling"] is True
    assert state["is_invulnerable"] is True
    assert state["on_cooldown"] is True
    assert state["direction"] == "WEST"
    assert state["cooldown_remaining"] == pytest.approx(DEFAULT_ROLL_COOLDOWN)
