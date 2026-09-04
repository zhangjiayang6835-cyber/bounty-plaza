"""Unit tests for Department of Ordinance and New Guns (D.O.N.G.) Expansion.
Resolves Issue #656: [BOUNTY] [$1000] [EASY] [AGENTIC AI] D.O.N.G. Expansion.
Upstream Reference: Iamgoofball/-tg-station#215.
"""

import pytest
from scripts.dong_expansion_engine import (
    DONGExpansionEngine,
    WeaponSpec,
    WeaponTier,
)


@pytest.fixture
def engine():
    return DONGExpansionEngine()


def test_station_map_layout_dimensions(engine):
    layout = engine.generate_station_map_layout()
    assert layout["dimensions"]["width"] == 15
    assert layout["dimensions"]["height"] == 15
    assert layout["total_tiles"] == 225

    # Check ascii layout contains walls, range, lab, armory, doors
    ascii_map = layout["ascii_map"]
    lines = ascii_map.splitlines()
    assert len(lines) == 15
    for line in lines:
        assert len(line) == 15

    assert "R" in ascii_map  # Firing range
    assert "L" in ascii_map  # Lab
    assert "A" in ascii_map  # Armory
    assert "D" in ascii_map  # Blast door airlock connector


def test_unprovoked_weapon_research_economy(engine):
    # Initial state
    assert engine.research_points == 0
    starter_weapon = engine.registered_weapons["laser_carbine_mk1"]
    assert starter_weapon.unlocked is True

    # Fire unprovoked shot at a clown
    res = engine.test_fire_weapon(
        weapon_id="laser_carbine_mk1",
        shooter="Chief Medical Officer",
        target="Clown",
        unprovoked=True
    )
    assert res["success"] is True
    assert res["rp_earned"] == 15
    assert engine.research_points == 15
    assert engine.unprovoked_incidents == 1


def test_provoked_fire_penalty(engine):
    # Provoked shot should award significantly fewer points
    res = engine.test_fire_weapon(
        weapon_id="laser_carbine_mk1",
        shooter="Security Officer",
        target="Syndicate Operative",
        unprovoked=False
    )
    assert res["success"] is True
    assert res["rp_earned"] == int(15 * 0.2)  # 3 RP


def test_weapon_unlock_progression(engine):
    # scatter_disabler requires 150 RP
    scatter = engine.registered_weapons["scatter_disabler"]
    assert scatter.unlocked is False

    # Fire 10 unprovoked shots: 10 * 15 = 150 RP
    for i in range(10):
        engine.test_fire_weapon(
            weapon_id="laser_carbine_mk1",
            shooter="Research Director",
            target=f"Target Dummy #{i}",
            unprovoked=True
        )

    assert engine.research_points >= 150
    assert scatter.unlocked is True


def test_custom_weapon_extensibility(engine):
    custom_gun = WeaponSpec(
        weapon_id="banana_cannon_v1",
        name="Slip-Stream Kinetic Banana Cannon",
        tier=WeaponTier.BASIC,
        required_rp=50,
        base_damage=5.0,
        rp_yield_per_shot=35,
        unlocked=False,
        description="Fires high velocity peels."
    )
    engine.register_custom_weapon(custom_gun)
    assert "banana_cannon_v1" in engine.registered_weapons


def test_expand_dong_awareness_broadcast(engine):
    initial_rp = engine.research_points
    broadcast = engine.expand_dong_broadcast()
    assert "Expand D.O.N.G.!" in broadcast["broadcast"]
    assert broadcast["bonus_rp_awarded"] == 100
    assert engine.research_points == initial_rp + 100


def test_dreammaker_export_syntax(engine):
    dm_code = engine.export_dreammaker_code()
    assert "/area/station/dong" in dm_code
    assert "/datum/department/dong" in dm_code
    assert "unprovoked_shot_counter" in dm_code
