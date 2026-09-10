"""Formal invariant verifier for Bedrock physics and potion effect scaling."""

from __future__ import annotations

from dataclasses import dataclass, field
from packages.bedrock_physics_effects.physics_engine import (
    BedrockPlayerPhysics,
    PotionEffect,
    Vector3,
)


@dataclass
class VerificationReport:
    """Consolidated summary of formal invariant verifications."""

    checks_run: int = 0
    checks_passed: int = 0
    all_passed: bool = False
    details: list[str] = field(default_factory=list)


class BedrockPhysicsVerifier:
    """Executes formal invariant checks against Bedrock physics engine."""

    @staticmethod
    def check_amplifier_scaling_overflow() -> bool:
        """Verify dynamic dampening does not collapse when amplifier exceeds 128."""
        player = BedrockPlayerPhysics()
        test_amplifiers = (0, 64, 128, 129, 130, 200, 255)
        last_multiplier = 0.0

        for amp in test_amplifiers:
            mult = player.calculate_dampening_multiplier(amp)
            if mult <= 1.0 and amp > 0:
                return False
            if mult <= last_multiplier:
                return False
            last_multiplier = mult

        amp_130_mult = player.calculate_dampening_multiplier(130)
        expected_130 = 1.0 + (130.0 / 256.0)
        return abs(amp_130_mult - expected_130) < 1e-6

    @staticmethod
    def check_velocity_vector_preservation() -> bool:
        """Verify 1-tick effect cycling maintains continuous velocity vectors."""
        player = BedrockPlayerPhysics(
            position=Vector3(0.0, 50.0, 0.0),
            velocity=Vector3(0.0, 0.0, 0.0),
        )
        jump_effect = PotionEffect("minecraft:jump_boost", 130, 1)

        for _ in range(10):
            player.apply_potion_effects([jump_effect])
            player.integrate_tick()

        return player.velocity.y < -0.5 and len(player.velocity_history) == 10

    @staticmethod
    def check_bedrock_gravity_bounds() -> bool:
        """Verify safe velocity bounds against internal gravity multiplier 0.08."""
        player = BedrockPlayerPhysics()
        player.pending_jump_boost = 130
        safe_vy = player.calculate_safe_velocity_threshold()
        res_safe = player.handle_fall_damage(2.0, -(safe_vy * 0.9))

        if res_safe.raw_damage != 0.0 or res_safe.final_health_damage != 0.0:
            return False

        player.pending_jump_boost = 130
        res_unsafe = player.handle_fall_damage(10.0, -(safe_vy * 2.0))
        return res_unsafe.raw_damage > 0.0

    @staticmethod
    def check_absorption_shield_mitigation() -> bool:
        """Verify absorption shield buffer accumulation and kinetic damage absorption."""
        player = BedrockPlayerPhysics(custom_shield_buffer=0.0)
        absorption_effect = PotionEffect("minecraft:absorption", 130, 1)
        player.apply_potion_effects([absorption_effect])
        expected_shield = 4.0 * (130 + 1)

        if abs(player.shield_buffer - expected_shield) > 1e-5:
            return False

        result = player.handle_fall_damage(20.0, -5.0)
        return result.shield_damage_absorbed > 0.0 and result.final_health_damage == 0.0

    @staticmethod
    def check_fall_dropout_anomaly_resolution() -> bool:
        """Verify anomaly fall_distance=0.00 vy=-1.84 m/s is mitigated."""
        player = BedrockPlayerPhysics(
            health=20.0,
            custom_shield_buffer=100.0,
            shield_buffer=20.0,
            pending_jump_boost=130,
        )
        result = player.handle_fall_damage(fall_distance=0.0, vy=-1.84)
        return result.final_health_damage == 0.0 and result.remaining_health == 20.0

    @staticmethod
    def check_high_fall_simulation() -> bool:
        """Simulate high vertical ascent/descent fall_y=42, amp=130, duration=1."""
        player = BedrockPlayerPhysics(health=20.0, custom_shield_buffer=100.0)
        res = player.simulate_fall_from_height(fall_height=42.0, amplifier=130, duration=1)
        return res.final_health_damage < 5.0 and res.lethal_prevented

    @classmethod
    def run_all_checks(cls) -> VerificationReport:
        """Execute all formal invariant checks and generate report."""
        checks = (
            cls.check_amplifier_scaling_overflow,
            cls.check_velocity_vector_preservation,
            cls.check_bedrock_gravity_bounds,
            cls.check_absorption_shield_mitigation,
            cls.check_fall_dropout_anomaly_resolution,
            cls.check_high_fall_simulation,
        )

        passed = 0
        details: list[str] = []
        for check in checks:
            success = check()
            if success:
                passed += 1
                details.append(f"PASS: {check.__name__}")
            else:
                details.append(f"FAIL: {check.__name__}")

        total = len(checks)
        return VerificationReport(
            checks_run=total,
            checks_passed=passed,
            all_passed=(passed == total),
            details=details,
        )
