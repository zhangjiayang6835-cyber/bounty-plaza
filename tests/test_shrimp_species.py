"""🦐 Unit & Integration Tests for Shrimp-Person Species Mechanics 🦐.
Resolves Issue #692: [Bounty $200] Add a shrimp-person species 🦐 🦐 🦐.
"""

import pytest
from scripts.shrimp_species import (
    ShrimpPerson,
    FishbowlHelmet,
    FriedShrimp,
    Entity,
    RespirationEnvironment,
    BYOND_SHRIMP_DM_SOURCE,
)


@pytest.fixture
def shrimp():
    """🦐 Fixture initializing an active shrimp-person 🦐."""
    return ShrimpPerson(
        entity_id="mob_shrimp_001",
        name="🦐 Clack-Clack Jenkins 🦐",
        x=5,
        y=5,
    )


def test_shrimp_antennae_t_ray_vision(shrimp):
    """🦐 Verifies permanent T-ray sensory vision on shrimp-people 🦐."""
    assert shrimp.t_ray_vision is True
    assert "🦐_antenna_t_ray" in shrimp.traits
    assert "🦐_chitin_shell" in shrimp.traits


def test_shrimp_fishbowl_respiration_in_air(shrimp):
    """🦐 Verifies that shrimp suffocate in air without fishbowl helmet, but survive when wearing one 🦐."""
    # In air without fishbowl -> suffocating
    assert shrimp.is_suffocating(RespirationEnvironment.AIR) is True

    # In water -> naturally breathes
    assert shrimp.is_suffocating(RespirationEnvironment.WATER) is False

    # Equip fishbowl helmet filled with water
    shrimp.head_gear = FishbowlHelmet(water_level_ml=500.0)
    assert shrimp.is_suffocating(RespirationEnvironment.AIR) is False
    assert shrimp.head_gear.water_level_ml == 499.0


def test_shrimp_spin_tail_whip_damages_adjacent_mobs_and_structures(shrimp):
    """🦐 Verifies that *spin triggers a tail whip damaging adjacent entities and structures 🦐."""
    adjacent_mob = Entity(entity_id="mob_human_1", name="Crewmember Bob", x=5, y=6, health=100.0)
    adjacent_wall = Entity(entity_id="struct_wall_1", name="Reinforced Wall", x=6, y=5, health=100.0, is_structure=True)
    distant_mob = Entity(entity_id="mob_human_2", name="Captain Far Away", x=10, y=10, health=100.0)

    surroundings = [adjacent_mob, adjacent_wall, distant_mob]
    result = shrimp.spin_tail_whip(surroundings)

    assert result["targets_hit"] == 2
    assert adjacent_mob.health == 75.0  # 100 - 25
    assert adjacent_wall.health == 75.0  # 100 - 25
    assert distant_mob.health == 100.0  # Out of range


def test_shrimp_death_burn_damage_transforms_to_fried_shrimp(shrimp):
    """🦐 Verifies that death with >= 50 burn damage converts the shrimp-person into fried shrimp 🍤!"""
    shrimp.burn_damage = 75.0
    fried_item = shrimp.die()

    assert shrimp.is_dead is True
    assert isinstance(fried_item, FriedShrimp)
    assert "🍤" in fried_item.name
    assert fried_item.is_food is True
    assert fried_item.nutrition_value == 45.0
    assert fried_item in shrimp.inventory


def test_shrimp_death_without_burn_does_not_fry(shrimp):
    """🦐 Verifies normal death without high burn damage does not turn into fried shrimp 🦐."""
    shrimp.brute_damage = 100.0
    shrimp.burn_damage = 10.0
    fried_item = shrimp.die()

    assert shrimp.is_dead is True
    assert fried_item is None


def test_byond_dm_source_module_structure():
    """🦐 Validates DM species definition, procs, and emoji presence 🦐."""
    assert "/datum/species/shrimp" in BYOND_SHRIMP_DM_SOURCE
    assert "TRAIT_T_RAY_VISION" in BYOND_SHRIMP_DM_SOURCE
    assert "fishbowl" in BYOND_SHRIMP_DM_SOURCE
    assert "spin_tail_whip" in BYOND_SHRIMP_DM_SOURCE
    assert "fried_shrimp" in BYOND_SHRIMP_DM_SOURCE
    assert BYOND_SHRIMP_DM_SOURCE.count("🦐") >= 10
