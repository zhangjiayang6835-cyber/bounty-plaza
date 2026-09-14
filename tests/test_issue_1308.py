"""Comprehensive test suite for Issue #1308 Bedrock physics fix."""

from packages.bedrock_physics_effects.physics_engine import (
    BedrockPlayerPhysics,
    PotionEffect,
    Vector3,
)
from packages.bedrock_physics_effects.verifier import BedrockPhysicsVerifier


def test_amplifier_scaling_no_overflow() -> None:
    """Verify dynamic dampening does not overflow or truncate for amplifiers above 128."""
    player = BedrockPlayerPhysics()
    cases = [
        (0, 1.0),
        (64, 1.25),
        (128, 1.5),
        (130, 1.0 + (130.0 / 256.0)),
        (200, 1.0 + (200.0 / 256.0)),
        (255, 1.0 + (255.0 / 256.0)),
    ]
    for amp, expected in cases:
        mult = player.calculate_dampening_multiplier(amp)
        assert abs(mult - expected) < 1e-6, f"Amplifier {amp} calculated {mult} != {expected}"


def test_velocity_vector_preservation() -> None:
    """Verify 1-tick potion effect application preserves velocity vectors."""
    player = BedrockPlayerPhysics(velocity=Vector3(1.5, -2.4, 3.2))
    initial_vy = player.velocity.y

    jump_effect = PotionEffect("minecraft:jump_boost", amplifier=130, duration=1)
    absorption_effect = PotionEffect("minecraft:absorption", amplifier=130, duration=1)
    player.apply_potion_effects([jump_effect, absorption_effect])

    assert player.velocity.x == 1.5
    assert player.velocity.y == initial_vy
    assert player.velocity.z == 3.2


def test_safe_velocity_threshold_bounds() -> None:
    """Verify safe velocity bounds against internal Bedrock gravity multiplier 0.08."""
    player = BedrockPlayerPhysics()
    player.pending_jump_boost = 0
    base_thresh = player.calculate_safe_velocity_threshold()
    assert abs(base_thresh - 3.0) < 1e-6

    player.pending_jump_boost = 130
    boost_thresh = player.calculate_safe_velocity_threshold()
    expected_boost_thresh = 3.0 * (1.0 + 130.0 / 256.0)
    assert abs(boost_thresh - expected_boost_thresh) < 1e-6

    safe_res = player.handle_fall_damage(fall_distance=2.0, vy=-3.5)
    assert safe_res.raw_damage == 0.0
    assert safe_res.final_health_damage == 0.0


def test_absorption_shield_buffer_accumulation() -> None:
    """Verify absorption shield buffer arithmetic and impact mitigation."""
    player = BedrockPlayerPhysics(custom_shield_buffer=0.0)
    absorption_effect = PotionEffect("minecraft:absorption", amplifier=130, duration=1)
    player.apply_potion_effects([absorption_effect])

    expected_shield = 4.0 * (130 + 1)
    assert abs(player.shield_buffer - expected_shield) < 1e-6

    result = player.handle_fall_damage(fall_distance=30.0, vy=-5.0)
    assert result.shield_damage_absorbed > 0.0
    assert result.final_health_damage == 0.0
    assert result.remaining_health == 20.0


def test_fall_dropout_anomaly_resolution() -> None:
    """Verify the reported anomaly fall_distance=0.00 vy=-1.84 m/s is mitigated."""
    player = BedrockPlayerPhysics(
        health=20.0,
        custom_shield_buffer=100.0,
        shield_buffer=20.0,
        pending_jump_boost=130,
    )
    result = player.handle_fall_damage(fall_distance=0.0, vy=-1.84)

    assert result.final_health_damage == 0.0
    assert result.remaining_health == 20.0
    assert result.lethal_prevented is True
    assert len(player.anomaly_warnings) == 1


def test_high_fall_simulation() -> None:
    """Simulate fall from y=42 with amplifier 130 and verify survival."""
    player = BedrockPlayerPhysics(health=20.0, custom_shield_buffer=100.0)
    result = player.simulate_fall_from_height(fall_height=42.0, amplifier=130, duration=1)

    assert result.final_health_damage < 5.0
    assert result.lethal_prevented is True
    assert result.remaining_health > 15.0


def test_vector3_operations() -> None:
    """Verify Vector3 kinematic arithmetic."""
    v1 = Vector3(1.0, 2.0, 3.0)
    v2 = Vector3(4.0, 5.0, 6.0)

    v_add = v1.add(v2)
    assert (v_add.x, v_add.y, v_add.z) == (5.0, 7.0, 9.0)

    v_sub = v2.sub(v1)
    assert (v_sub.x, v_sub.y, v_sub.z) == (3.0, 3.0, 3.0)

    v_scale = v1.scale(2.0)
    assert (v_scale.x, v_scale.y, v_scale.z) == (2.0, 4.0, 6.0)

    assert v1.length_squared() == 14.0
    assert abs(v1.length() - 3.741657) < 1e-4

    v_clone = v1.clone()
    assert (v_clone.x, v_clone.y, v_clone.z) == (1.0, 2.0, 3.0)


def test_verifier_all_checks() -> None:
    """Verify BedrockPhysicsVerifier reports all 6 invariants passing."""
    report = BedrockPhysicsVerifier.run_all_checks()
    assert report.all_passed is True
    assert report.checks_passed == 6
    assert report.checks_run == 6
