"""Dodge rolling mechanic with temporary invulnerability frames.

While a living entity is dodge rolling, incoming damage is fully mitigated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple


# Defaults mirror typical SS13-style timing (seconds).
DEFAULT_ROLL_DURATION = 0.7
DEFAULT_ROLL_COOLDOWN = 2.5
DEFAULT_ROLL_DISTANCE = 3

# Cardinal / diagonal direction vectors (dx, dy).
DIRECTIONS = {
    "NORTH": (0, 1),
    "SOUTH": (0, -1),
    "EAST": (1, 0),
    "WEST": (-1, 0),
    "NORTHEAST": (1, 1),
    "NORTHWEST": (-1, 1),
    "SOUTHEAST": (1, -1),
    "SOUTHWEST": (-1, -1),
}


@dataclass
class LivingEntity:
    """Minimal combat entity that can dodge roll and take damage."""

    name: str
    health: float = 100.0
    max_health: float = 100.0
    x: float = 0.0
    y: float = 0.0
    facing: str = "NORTH"
    conscious: bool = True
    standing: bool = True
    immobilized: bool = False
    buckled: bool = False
    _traits: set = field(default_factory=set)
    _dodge: Optional["DodgeRollController"] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self._dodge is None:
            self._dodge = DodgeRollController(self)

    @property
    def is_invulnerable(self) -> bool:
        return "GODMODE" in self._traits or (
            self._dodge is not None and self._dodge.is_rolling
        )

    def add_trait(self, trait: str) -> None:
        self._traits.add(trait)

    def remove_trait(self, trait: str) -> None:
        self._traits.discard(trait)

    def has_trait(self, trait: str) -> bool:
        return trait in self._traits

    def can_move(self) -> bool:
        return (
            self.conscious
            and self.standing
            and not self.immobilized
            and not self.buckled
        )

    def apply_damage(self, amount: float, forced: bool = False) -> float:
        """Apply damage; returns amount actually taken.

        While dodge rolling (or otherwise invulnerable), damage is zeroed
        unless ``forced`` is True.
        """
        if amount <= 0:
            return 0.0
        if not forced and self.is_invulnerable:
            return 0.0
        taken = min(amount, self.health)
        self.health -= taken
        if self.health <= 0:
            self.health = 0.0
            self.conscious = False
        return taken

    def dodge_roll(self, direction: Optional[str] = None, now: float = 0.0) -> bool:
        """Attempt a dodge roll. Returns True if the roll started."""
        assert self._dodge is not None
        return self._dodge.attempt(direction=direction, now=now)

    def tick(self, now: float) -> None:
        """Advance dodge-roll timers to the given absolute time."""
        assert self._dodge is not None
        self._dodge.tick(now)


class DodgeRollController:
    """Owns roll state, cooldown, movement, and invulnerability frames."""

    TRAIT_SOURCE = "dodge_rolling"

    def __init__(
        self,
        owner: LivingEntity,
        duration: float = DEFAULT_ROLL_DURATION,
        cooldown: float = DEFAULT_ROLL_COOLDOWN,
        distance: float = DEFAULT_ROLL_DISTANCE,
    ) -> None:
        self.owner = owner
        self.duration = duration
        self.cooldown = cooldown
        self.distance = distance
        self.is_rolling = False
        self.roll_started_at: Optional[float] = None
        self.cooldown_until: float = 0.0
        self.roll_direction: Optional[str] = None

    def is_on_cooldown(self, now: float) -> bool:
        return now < self.cooldown_until

    def cooldown_remaining(self, now: float) -> float:
        return max(0.0, self.cooldown_until - now)

    def can_roll(self, now: float = 0.0) -> bool:
        owner = self.owner
        if not owner.can_move():
            return False
        if self.is_rolling:
            return False
        if self.is_on_cooldown(now):
            return False
        return True

    def attempt(self, direction: Optional[str] = None, now: float = 0.0) -> bool:
        if not self.can_roll(now):
            return False

        roll_dir = direction or self.owner.facing
        if roll_dir not in DIRECTIONS:
            return False

        self.is_rolling = True
        self.roll_started_at = now
        self.roll_direction = roll_dir
        self.cooldown_until = now + self.cooldown

        self.owner.add_trait("GODMODE")
        self.owner.facing = roll_dir
        self._apply_movement(roll_dir)
        return True

    def _apply_movement(self, direction: str) -> None:
        dx, dy = DIRECTIONS[direction]
        # Normalize diagonal travel so total displacement ≈ distance.
        length = (dx * dx + dy * dy) ** 0.5
        scale = self.distance / length if length else 0.0
        self.owner.x += dx * scale
        self.owner.y += dy * scale

    def tick(self, now: float) -> None:
        if not self.is_rolling or self.roll_started_at is None:
            return
        if now - self.roll_started_at >= self.duration:
            self._end_roll()

    def _end_roll(self) -> None:
        self.is_rolling = False
        self.roll_started_at = None
        self.roll_direction = None
        self.owner.remove_trait("GODMODE")

    def cancel(self) -> None:
        if self.is_rolling:
            self._end_roll()

    def state(self, now: float = 0.0) -> dict:
        return {
            "is_rolling": self.is_rolling,
            "is_invulnerable": self.owner.is_invulnerable,
            "on_cooldown": self.is_on_cooldown(now),
            "cooldown_remaining": self.cooldown_remaining(now),
            "direction": self.roll_direction,
            "position": (self.owner.x, self.owner.y),
        }


def resolve_direction(facing: str, intended: Optional[str] = None) -> str:
    """Prefer intended movement direction, otherwise facing direction."""
    if intended and intended in DIRECTIONS:
        return intended
    if facing in DIRECTIONS:
        return facing
    return "NORTH"


def position_delta(before: Tuple[float, float], after: Tuple[float, float]) -> float:
    """Euclidean distance between two positions."""
    dx = after[0] - before[0]
    dy = after[1] - before[1]
    return (dx * dx + dy * dy) ** 0.5
