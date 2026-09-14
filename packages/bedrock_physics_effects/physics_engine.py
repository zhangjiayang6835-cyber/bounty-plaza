"""Bedrock kinematic physics engine and 1-tick potion effect simulator.

Resolves fall damage calculation anomalies, amplifier precision overflows,
velocity preservation across tick boundaries, and custom shield mitigations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class Vector3:
    """Three-dimensional kinematic vector."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def add(self, other: Vector3) -> Vector3:
        """Add another vector to this vector."""
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def sub(self, other: Vector3) -> Vector3:
        """Subtract another vector from this vector."""
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def scale(self, factor: float) -> Vector3:
        """Scale this vector by a scalar factor."""
        return Vector3(self.x * factor, self.y * factor, self.z * factor)

    def length_squared(self) -> float:
        """Compute squared magnitude of this vector."""
        return self.x * self.x + self.y * self.y + self.z * self.z

    def length(self) -> float:
        """Compute magnitude of this vector."""
        return math.sqrt(self.length_squared())

    def clone(self) -> Vector3:
        """Create an independent copy of this vector."""
        return Vector3(self.x, self.y, self.z)


@dataclass
class PotionEffect:
    """Represents an active or 1-tick cycled status effect."""

    effect_type: str
    amplifier: int
    duration: int
    ambient: bool = False
    show_particles: bool = False


@dataclass
class PlayerPhysicsConfig:
    """Kinematic parameters aligned with Bedrock physics specifications."""

    gravity: float = 0.08
    air_drag: float = 0.98
    base_safe_threshold: float = 3.0
    base_max_health: float = 20.0
    absorption_hp_per_amplifier: float = 4.0
    amplifier_scale_factor: float = 256.0


@dataclass
class ShieldDamageBreakdown:
    """Detailed breakdown of damage absorbed by buffers."""

    absorption_absorbed: float = 0.0
    custom_shield_absorbed: float = 0.0
    safe_threshold: float = 3.0
    dampening_multiplier: float = 1.0


@dataclass
class DamageResult:
    """Outcome of impact fall damage resolution."""

    fall_distance: float
    velocity_y: float
    raw_damage: float
    final_health_damage: float
    remaining_health: float
    lethal_prevented: bool
    breakdown: ShieldDamageBreakdown = field(default_factory=ShieldDamageBreakdown)

    @property
    def shield_damage_absorbed(self) -> float:
        """Absorption buffer component absorbed."""
        return self.breakdown.absorption_absorbed

    @property
    def custom_shield_absorbed(self) -> float:
        """Custom attribute shield component absorbed."""
        return self.breakdown.custom_shield_absorbed

    @property
    def safe_threshold(self) -> float:
        """Safe velocity threshold applied during resolution."""
        return self.breakdown.safe_threshold

    @property
    def dampening_multiplier(self) -> float:
        """Dampening multiplier derived from jump boost amplifier."""
        return self.breakdown.dampening_multiplier


@dataclass
class KinematicTelemetry:
    """Diagnostic tracking container for anomaly warnings and velocity history."""

    anomaly_warnings: list[str] = field(default_factory=list)
    velocity_history: list[float] = field(default_factory=list)
    config: PlayerPhysicsConfig = field(default_factory=PlayerPhysicsConfig)


@dataclass
class BedrockPlayerPhysics:
    """Simulates Bedrock kinematic motion and 1-tick potion effect cycling."""

    position: Vector3 = field(default_factory=lambda: Vector3(0.0, 100.0, 0.0))
    velocity: Vector3 = field(default_factory=lambda: Vector3(0.0, 0.0, 0.0))
    health: float = 20.0
    shield_buffer: float = 0.0
    custom_shield_buffer: float = 100.0
    pending_jump_boost: int = 0
    telemetry: KinematicTelemetry = field(default_factory=KinematicTelemetry)

    @property
    def config(self) -> PlayerPhysicsConfig:
        """Kinematic physics configuration."""
        return self.telemetry.config

    @property
    def anomaly_warnings(self) -> list[str]:
        """Recorded anomaly warnings."""
        return self.telemetry.anomaly_warnings

    @property
    def velocity_history(self) -> list[float]:
        """Historical vertical velocity recordings."""
        return self.telemetry.velocity_history

    def calculate_dampening_multiplier(self, amplifier: int) -> float:
        """Calculate dynamic dampening multiplier using double precision arithmetic.

        Guarantees that amplifier values greater than 128 do not experience
        signed 8-bit integer truncation or collapse to zero.
        """
        amp_double = float(max(0, amplifier))
        return 1.0 + (amp_double / self.config.amplifier_scale_factor)

    def apply_potion_effects(self, effects: list[PotionEffect]) -> None:
        """Apply status effects without resetting kinematic velocity vectors.

        Maintains velocity vector continuity across sub-tick and tick transitions.
        """
        for effect in effects:
            if effect.effect_type == "minecraft:jump_boost" and effect.duration <= 1:
                multiplier = self.calculate_dampening_multiplier(effect.amplifier)
                self.custom_shield_buffer *= multiplier
                self.pending_jump_boost = effect.amplifier

            elif effect.effect_type == "minecraft:absorption" and effect.duration <= 1:
                bonus = self.config.absorption_hp_per_amplifier * float(effect.amplifier + 1)
                self.shield_buffer += bonus

    def calculate_safe_velocity_threshold(self) -> float:
        """Derive the dynamic safe downward velocity threshold before damage occurs."""
        boost_term = float(self.pending_jump_boost) / self.config.amplifier_scale_factor
        return self.config.base_safe_threshold * (1.0 + boost_term)

    def handle_fall_damage(self, fall_distance: float, vy: float) -> DamageResult:
        """Resolve kinetic impact damage with custom shield and absorption buffers."""
        safe_threshold = self.calculate_safe_velocity_threshold()
        dampening = self.calculate_dampening_multiplier(self.pending_jump_boost)

        if fall_distance <= 0.001 and vy < -0.5:
            self.telemetry.anomaly_warnings.append(
                f"Anomaly detected: fall_distance={fall_distance:.2f}, vy={vy:.2f}"
            )

        raw_damage = 0.0
        if vy < -safe_threshold:
            kinetic_height = (vy * vy) / (2.0 * self.config.gravity)
            raw_damage = max(0.0, kinetic_height - self.config.base_safe_threshold)

        absorbed_absorption = min(self.shield_buffer, raw_damage)
        self.shield_buffer -= absorbed_absorption
        unabsorbed = raw_damage - absorbed_absorption

        absorbed_custom = min(self.custom_shield_buffer, unabsorbed)
        self.custom_shield_buffer -= absorbed_custom
        final_health_damage = max(0.0, unabsorbed - absorbed_custom)

        self.health = max(0.0, self.health - final_health_damage)
        self.pending_jump_boost = 0

        breakdown = ShieldDamageBreakdown(
            absorption_absorbed=absorbed_absorption,
            custom_shield_absorbed=absorbed_custom,
            safe_threshold=safe_threshold,
            dampening_multiplier=dampening,
        )

        return DamageResult(
            fall_distance=fall_distance,
            velocity_y=vy,
            raw_damage=raw_damage,
            final_health_damage=final_health_damage,
            remaining_health=self.health,
            lethal_prevented=self.health > 0.0,
            breakdown=breakdown,
        )

    def integrate_tick(self, vertical_impulse: float = 0.0) -> None:
        """Advance kinematic simulation by one physics tick."""
        net_acceleration = vertical_impulse - self.config.gravity
        updated_vy = (self.velocity.y + net_acceleration) * self.config.air_drag
        self.velocity.y = updated_vy
        self.position.y += self.velocity.y
        self.telemetry.velocity_history.append(self.velocity.y)

    def simulate_fall_from_height(
        self,
        fall_height: float,
        amplifier: int = 130,
        duration: int = 1,
    ) -> DamageResult:
        """Simulate high vertical descent with 1-tick cycled potion effects."""
        self.position.y = fall_height
        self.velocity.y = 0.0
        self.telemetry.velocity_history.clear()

        jump_effect = PotionEffect("minecraft:jump_boost", amplifier, duration)
        absorption_effect = PotionEffect("minecraft:absorption", amplifier, duration)
        effects = [jump_effect, absorption_effect]

        accumulated_fall_distance = 0.0
        while self.position.y > 0.0:
            self.apply_potion_effects(effects)
            self.integrate_tick()
            if self.velocity.y < 0.0:
                accumulated_fall_distance += abs(self.velocity.y)

        impact_vy = self.velocity.y
        return self.handle_fall_damage(accumulated_fall_distance, impact_vy)
