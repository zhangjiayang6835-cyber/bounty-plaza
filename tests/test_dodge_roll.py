"""Unit and combat mechanics test suite for Dodge Rolling & i-Frames.
Resolves Issue #710: Implement Dodge Rolling ($50 USD).
"""

import time
import pytest
from scripts.dodge_roll import (
    CombatEntity,
    Direction,
    EntityState,
    DodgeRollError,
)


@pytest.fixture
def player():
    return CombatEntity(
        name="SecurityOfficer",
        max_health=100.0,
        max_stamina=100.0,
        roll_duration=0.5,
        roll_cooldown=0.2,
        roll_speed=10.0,
        roll_stamina_cost=25.0,
    )


def test_initial_state_idle_and_vulnerable(player):
    assert player.state == EntityState.IDLE
    assert player.is_invulnerable is False
    assert player.health == 100.0
    assert player.stamina == 100.0


def test_damage_taken_when_not_rolling(player):
    res = player.take_damage(35.0)
    assert res["damage_taken"] == 35.0
    assert res["damage_blocked"] == 0.0
    assert res["invulnerable"] is False
    assert player.health == 65.0


def test_dodge_roll_provides_complete_damage_invulnerability(player):
    """Core Requirement: Cannot take damage while dodge rolling."""
    # Initiate dodge roll to the East
    roll_info = player.execute_dodge_roll(Direction.EAST)
    assert roll_info["status"] == "ROLLING"
    assert roll_info["invulnerable"] is True
    assert player.is_invulnerable is True
    assert player.stamina == 75.0

    # Attack player during dodge roll
    combat_res = player.take_damage(50.0, damage_type="explosion")
    assert combat_res["damage_taken"] == 0.0
    assert combat_res["damage_blocked"] == 50.0
    assert combat_res["invulnerable"] is True
    assert "DODGE" in combat_res["message"]
    # Health remains completely untouched
    assert player.health == 100.0


def test_kinetic_displacement_directional_movement(player):
    initial_x, initial_y = player.x, player.y
    # Roll North: speed 10 * duration 0.5 = 5.0 units displacement along Y
    player.execute_dodge_roll(Direction.NORTH)
    assert player.x == initial_x
    assert player.y == initial_y + 5.0


def test_stamina_cost_exhaustion_blocks_roll(player):
    player.execute_dodge_roll(Direction.NORTH)  # 75 left
    player.state = EntityState.IDLE
    player.execute_dodge_roll(Direction.NORTH)  # 50 left
    player.state = EntityState.IDLE
    player.execute_dodge_roll(Direction.NORTH)  # 25 left
    player.state = EntityState.IDLE
    player.execute_dodge_roll(Direction.NORTH)  # 0 left
    player.state = EntityState.IDLE

    # 5th attempt: no stamina
    with pytest.raises(DodgeRollError, match="Insufficient stamina"):
        player.execute_dodge_roll(Direction.NORTH)


def test_rolling_state_transitions_to_cooldown_and_idle(player):
    # Short roll duration for fast execution
    fast_player = CombatEntity(roll_duration=0.1, roll_cooldown=0.1)
    fast_player.execute_dodge_roll(Direction.WEST)
    assert fast_player.state == EntityState.ROLLING
    assert fast_player.is_invulnerable is True

    # After roll finishes
    time.sleep(0.12)
    fast_player._update_state()
    assert fast_player.state == EntityState.COOLDOWN
    assert fast_player.is_invulnerable is False

    # After cooldown finishes
    time.sleep(0.12)
    fast_player._update_state()
    assert fast_player.state == EntityState.IDLE


def test_consecutive_roll_blocked_while_already_rolling(player):
    player.execute_dodge_roll(Direction.SOUTH)
    with pytest.raises(DodgeRollError, match="Already rolling"):
        player.execute_dodge_roll(Direction.SOUTH)


def test_stamina_regeneration(player):
    player.execute_dodge_roll(Direction.EAST)
    assert player.stamina == 75.0
    player.regenerate_stamina(15.0)
    assert player.stamina == 90.0
    player.regenerate_stamina(50.0)
    assert player.stamina == 100.0  # Capped at max
