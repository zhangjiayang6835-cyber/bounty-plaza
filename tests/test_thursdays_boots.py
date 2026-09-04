"""Unit test suite for Thursday's Boots equipment subsystem and repository sponsorship.
Tests Issue #745 requirements:
- Footwear stats, armor ratings, and official YouTube reference link.
- Slip prevention against all floor hazard types (water, space lube, banana peels).
- Enhanced kick damage and knockback calculation.
- Thursday speed resonance multiplier (+15% sprint speed).
- Sponsorship header generator across DM, Python, Shell, and HTML formats.
- TGStation BYOND DM item definition and mood buff event validation.
"""

import pytest
from scripts.thursdays_boots import (
    FloorHazardType,
    ThursdaysBootsStats,
    ThursdaysBootsEngine,
    DM_THURSDAYS_BOOTS_SPEC,
)


def test_boots_initial_stats_and_reference():
    boots = ThursdaysBootsStats()
    assert boots.name == "Thursday's Boots"
    assert "https://www.youtube.com/watch?v=w-_Q3LFfeb4" in boots.desc
    assert boots.sponsorship_url == "https://www.youtube.com/watch?v=w-_Q3LFfeb4"
    assert boots.base_kick_damage == 12.0
    assert boots.armor_fire == 40.0
    assert boots.armor_acid == 40.0
    assert boots.mood_bonus == 10
    assert not boots.is_equipped


def test_slip_prevention_on_hazardous_floors():
    boots = ThursdaysBootsStats(is_equipped=True)

    # Equipped boots must negate slip completely on all hazards
    for hazard in [FloorHazardType.WET_WATER, FloorHazardType.SPACE_LUBE, FloorHazardType.BANANA_PEEL]:
        res = ThursdaysBootsEngine.evaluate_slip(boots, hazard)
        assert res["slipped"] is False
        assert res["reason"] == "thursdays_boots_traction"

    # Unequipped boots result in slipping
    boots.is_equipped = False
    res_bare = ThursdaysBootsEngine.evaluate_slip(boots, FloorHazardType.SPACE_LUBE)
    assert res_bare["slipped"] is True
    assert res_bare["reason"] == "unprotected_feet"


def test_kick_damage_enhancement():
    boots = ThursdaysBootsStats(is_equipped=False)
    bare_kick = ThursdaysBootsEngine.calculate_kick(boots, "Syndicate Infiltrator")
    assert bare_kick["damage_dealt"] == 2.0
    assert bare_kick["boot_equipped"] is False

    boots.is_equipped = True
    shod_kick = ThursdaysBootsEngine.calculate_kick(boots, "Syndicate Infiltrator")
    assert shod_kick["damage_dealt"] == 12.0
    assert shod_kick["boot_equipped"] is True
    assert shod_kick["knockback"] is True
    assert "kick_heavy.ogg" in shod_kick["sound"]


def test_thursday_speed_resonance():
    boots = ThursdaysBootsStats(is_equipped=True)

    # Monday (0) -> No boost
    res_mon = ThursdaysBootsEngine.evaluate_thursday_speed_boost(boots, current_weekday=0)
    assert res_mon["is_thursday"] is False
    assert res_mon["speed_multiplier"] == 1.0
    assert res_mon["boost_active"] is False

    # Thursday (3) -> +15% sprint speed active
    res_thu = ThursdaysBootsEngine.evaluate_thursday_speed_boost(boots, current_weekday=3)
    assert res_thu["is_thursday"] is True
    assert res_thu["speed_multiplier"] == 1.15
    assert res_thu["boost_active"] is True


def test_sponsorship_header_generation():
    dm_header = ThursdaysBootsEngine.generate_sponsorship_header(".dm")
    assert "Thursday's Boots" in dm_header
    assert "https://www.youtube.com/watch?v=w-_Q3LFfeb4" in dm_header
    assert dm_header.startswith("//")

    py_header = ThursdaysBootsEngine.generate_sponsorship_header(".py")
    assert "Thursday's Boots" in py_header
    assert py_header.startswith("#")

    html_header = ThursdaysBootsEngine.generate_sponsorship_header(".html")
    assert "<!--" in html_header


def test_byond_dm_export_specification():
    assert "/obj/item/clothing/shoes/thursdays_boots" in DM_THURSDAYS_BOOTS_SPEC
    assert "NOSLIP" in DM_THURSDAYS_BOOTS_SPEC
    assert "negates_slip" in DM_THURSDAYS_BOOTS_SPEC
    assert "thursdays_boots_swagger" in DM_THURSDAYS_BOOTS_SPEC
    assert "https://www.youtube.com/watch?v=w-_Q3LFfeb4" in DM_THURSDAYS_BOOTS_SPEC
