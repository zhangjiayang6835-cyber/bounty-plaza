"""Dodge Rolling & Invulnerability Frame (i-Frame) Combat Mechanics Engine.
Resolves Issue #710: Implement Dodge Rolling ($50 USD).

Implements:
1. Directional dodge roll with kinetic displacement and velocity.
2. Invulnerability frames (i-frames) completely negating damage while rolling.
3. State machine handling transitions (IDLE, MOVING, ROLLING, COOLDOWN, STUNNED).
4. Stamina cost and cooldown timer management.
"""

import math
import time
from enum import Enum
from typing import Any, Dict, Optional, Tuple


class EntityState(str, Enum):
    IDLE = "IDLE"
    MOVING = "MOVING"
    ROLLING = "ROLLING"
    COOLDOWN = "COOLDOWN"
    STUNNED = "STUNNED"


class Direction(str, Enum):
    NORTH = "NORTH"
    SOUTH = "SOUTH"
    EAST = "EAST"
    WEST = "WEST"
    NORTHEAST = "NORTHEAST"
    NORTHWEST = "NORTHWEST"
    SOUTHEAST = "SOUTHEAST"
    SOUTHWEST = "SOUTHWEST"


DIRECTION_VECTORS: Dict[Direction, Tuple[float, float]] = {
    Direction.NORTH: (0.0, 1.0),
    Direction.SOUTH: (0.0, -1.0),
    Direction.EAST: (1.0, 0.0),
    Direction.WEST: (-1.0, 0.0),
    Direction.NORTHEAST: (math.isqrt(2) / 2 or 0.7071, 0.7071),
    Direction.NORTHWEST: (-0.7071, 0.7071),
    Direction.SOUTHEAST: (0.7071, -0.7071),
    Direction.SOUTHWEST: (-0.7071, -0.7071),
}


class DodgeRollError(ValueError):
    """Base exception for dodge roll mechanic errors."""
    pass


class CombatEntity:
    """Game entity capable of executing dodge rolls with invulnerability frames."""

    def __init__(
        self,
        name: str = "Player",
        max_health: float = 100.0,
        max_stamina: float = 100.0,
        roll_duration: float = 0.5,       # Duration of dodge roll in seconds
        roll_cooldown: float = 0.3,       # Cooldown after roll finishes
        roll_speed: float = 8.0,          # Units per second during roll
        roll_stamina_cost: float = 25.0,
    ):
        self.name = name
        self.max_health = max_health
        self.health = max_health
        self.max_stamina = max_stamina
        self.stamina = max_stamina

        self.roll_duration = roll_duration
        self.roll_cooldown = roll_cooldown
        self.roll_speed = roll_speed
        self.roll_stamina_cost = roll_stamina_cost

        # Coordinates
        self.x: float = 0.0
        self.y: float = 0.0

        # State tracking
        self.state: EntityState = EntityState.IDLE
        self._roll_start_time: Optional[float] = None
        self._roll_end_time: Optional[float] = None
        self._roll_direction: Optional[Direction] = None

    @property
    def is_invulnerable(self) -> bool:
        """Entity cannot take damage while in the ROLLING state (invulnerability frames)."""
        self._update_state()
        return self.state == EntityState.ROLLING

    def _update_state(self) -> None:
        """Updates internal state machine based on elapsed time."""
        if self.state == EntityState.ROLLING and self._roll_start_time is not None:
            now = time.time()
            elapsed = now - self._roll_start_time
            if elapsed >= self.roll_duration:
                # Roll completed, enter cooldown period
                self.state = EntityState.COOLDOWN
                self._roll_end_time = self._roll_start_time + self.roll_duration

        if self.state == EntityState.COOLDOWN and self._roll_end_time is not None:
            now = time.time()
            if now - self._roll_end_time >= self.roll_cooldown:
                self.state = EntityState.IDLE
                self._roll_start_time = None
                self._roll_end_time = None
                self._roll_direction = None

    def can_roll(self) -> Tuple[bool, Optional[str]]:
        """Checks if entity is eligible to execute a dodge roll."""
        self._update_state()
        if self.state == EntityState.ROLLING:
            return False, "Already rolling"
        if self.state == EntityState.COOLDOWN:
            return False, "Roll on cooldown"
        if self.state == EntityState.STUNNED:
            return False, "Cannot roll while stunned"
        if self.stamina < self.roll_stamina_cost:
            return False, "Insufficient stamina"
        return True, None

    def execute_dodge_roll(self, direction: Direction, mock_time: Optional[float] = None) -> Dict[str, Any]:
        """Executes a directional dodge roll, initiating invulnerability frames."""
        eligible, reason = self.can_roll()
        if not eligible:
            raise DodgeRollError(f"Cannot execute dodge roll: {reason}")

        # Deduct stamina
        self.stamina = max(0.0, round(self.stamina - self.roll_stamina_cost, 2))

        # Transition state to ROLLING
        self.state = EntityState.ROLLING
        now = mock_time if mock_time is not None else time.time()
        self._roll_start_time = now
        self._roll_direction = direction

        # Calculate position displacement
        dx, dy = DIRECTION_VECTORS.get(direction, (0.0, 0.0))
        displacement = self.roll_speed * self.roll_duration
        self.x = round(self.x + dx * displacement, 3)
        self.y = round(self.y + dy * displacement, 3)

        return {
            "status": "ROLLING",
            "direction": direction.value,
            "invulnerable": True,
            "position": (self.x, self.y),
            "stamina_remaining": self.stamina,
            "duration": self.roll_duration,
        }

    def take_damage(self, damage_amount: float, damage_type: str = "physical") -> Dict[str, Any]:
        """Applies damage to entity, strictly checking for roll invulnerability frames."""
        if damage_amount <= 0:
            return {"damage_taken": 0.0, "current_health": self.health, "invulnerable": self.is_invulnerable}

        self._update_state()

        # Core Bounty Requirement: "you can't take damage while doing so"
        if self.is_invulnerable:
            return {
                "damage_taken": 0.0,
                "damage_blocked": damage_amount,
                "current_health": self.health,
                "invulnerable": True,
                "message": f"DODGE! Damage completely negated by dodge roll i-frames.",
            }

        actual_damage = min(self.health, damage_amount)
        self.health = max(0.0, round(self.health - actual_damage, 2))

        return {
            "damage_taken": actual_damage,
            "damage_blocked": 0.0,
            "current_health": self.health,
            "invulnerable": False,
            "is_alive": self.health > 0.0,
        }

    def regenerate_stamina(self, amount: float) -> float:
        """Restores stamina up to max_stamina."""
        self.stamina = min(self.max_stamina, round(self.stamina + amount, 2))
        return self.stamina
