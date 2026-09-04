"""Unit and regression test suite for quadratic projectile reflectivity.
Resolves Issue #649: [Bounty $145] Increase Reflectivity of projectile/energy/proj_weak_laser_2
Based On Angle Of Impact with /turf/wall/reflective.
"""

import pytest
from scripts.projectile_reflectivity import (
    ReflectiveWall,
    WallReflectiveType,
    WeakLaser2Projectile,
    BYOND_REFLECTIVE_DM_SOURCE,
)


@pytest.fixture
def standard_wall():
    return ReflectiveWall(wall_type=WallReflectiveType.STANDARD)


@pytest.fixture
def random_wall():
    return ReflectiveWall(wall_type=WallReflectiveType.RANDOM)


def test_quadratic_reflectivity_curve(standard_wall):
    """Verifies that reflectivity scales quadratically from 0 to 90 degrees."""
    # At 0 degrees: base reflectivity
    p0 = standard_wall.calculate_reflectivity_probability(0.0)
    assert p0 == pytest.approx(0.15, abs=1e-4)

    # At 45 degrees: ratio 0.5 -> quadratic ratio 0.25 -> 0.15 + (0.98 - 0.15) * 0.25 = 0.3575
    p45 = standard_wall.calculate_reflectivity_probability(45.0)
    assert p45 == pytest.approx(0.3575, abs=1e-4)

    # At 90 degrees: max reflectivity
    p90 = standard_wall.calculate_reflectivity_probability(90.0)
    assert p90 == pytest.approx(0.98, abs=1e-4)

    # Intermediate monotonicity check
    p30 = standard_wall.calculate_reflectivity_probability(30.0)
    p60 = standard_wall.calculate_reflectivity_probability(60.0)
    assert p0 < p30 < p45 < p60 < p90


def test_standard_reflection_angle_clamped_to_89_degrees(standard_wall):
    """Verifies minimum reflection angle is 0 and maximum is clamped strictly to 89 degrees."""
    assert standard_wall.calculate_reflection_angle(0.0) == 0.0
    assert standard_wall.calculate_reflection_angle(45.0) == 45.0
    assert standard_wall.calculate_reflection_angle(89.0) == 89.0
    # Over 89 degrees must clamp to 89 degrees
    assert standard_wall.calculate_reflection_angle(90.0) == 89.0
    assert standard_wall.calculate_reflection_angle(120.0) == 89.0


def test_random_wall_reflection_angle_between_0_and_180(random_wall):
    """Verifies /turf/wall/reflective/random scatters at random angles in [0, 180]."""
    for seed in range(20):
        angle = random_wall.calculate_reflection_angle(incident_angle_deg=45.0, rng_seed=seed)
        assert 0.0 <= angle <= 180.0


def test_projectile_successful_reflection(standard_wall):
    """Verifies projectile bounce, angle update, and reflection counter."""
    proj = WeakLaser2Projectile()
    # Force roll = 0.1, guaranteed < prob at 45 deg (~0.3575)
    res = proj.impact_reflective_wall(standard_wall, incident_angle_deg=45.0, rng_roll=0.1)

    assert res["reflected"] is True
    assert res["reflections_count"] == 1
    assert res["reflection_angle"] == 45.0
    assert proj.current_angle == 45.0


def test_projectile_absorption_on_failed_roll(standard_wall):
    """Verifies projectile failure when rng roll exceeds reflectivity probability."""
    proj = WeakLaser2Projectile()
    # Force roll = 0.99, higher than max reflectivity (0.98)
    res = proj.impact_reflective_wall(standard_wall, incident_angle_deg=45.0, rng_roll=0.99)

    assert res["reflected"] is False
    assert res["reason"] == "reflection_failed_absorbed"
    assert proj.reflections_count == 0


def test_projectile_max_reflections_limit(standard_wall):
    """Verifies projectile stops reflecting after reaching maximum allowed bounces."""
    proj = WeakLaser2Projectile(max_reflections=3, reflections_count=3)
    res = proj.impact_reflective_wall(standard_wall, incident_angle_deg=45.0, rng_roll=0.01)

    assert res["reflected"] is False
    assert res["reason"] == "max_reflections_reached"


def test_byond_dm_reflective_source_structure():
    """Verifies DM code snippet contains all required types and procs."""
    assert "/obj/projectile/energy/proj_weak_laser_2" in BYOND_REFLECTIVE_DM_SOURCE
    assert "/turf/closed/wall/reflective" in BYOND_REFLECTIVE_DM_SOURCE
    assert "/turf/closed/wall/reflective/random" in BYOND_REFLECTIVE_DM_SOURCE
    assert "clamp(incident_angle, 0, 89)" in BYOND_REFLECTIVE_DM_SOURCE
    assert "rand(0, 180)" in BYOND_REFLECTIVE_DM_SOURCE
