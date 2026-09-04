"""Unit tests for Cyborg Hand-on-a-Stick Combat Buff & Retaliation Subsystem.
Resolves Issue #647: [BOUNTY] [$300] Cyborg Buff By Adding Hand On Stick That Kills Anyone That Punches The Cyborg.
Upstream Reference: Iamgoofball/-tg-station#141.
"""

import pytest
from scripts.cyborg_hand_on_stick_buff import (
    CyborgHandOnStickBuff,
    MobState,
    MobType,
    BespokeTuesdayRNG,
)


@pytest.fixture
def cyborg_hand():
    return CyborgHandOnStickBuff(cyborg_id="Borg-Delta-9")


def test_allowed_ranges_and_tuesday_bypass(cyborg_hand):
    # Standard day (Wednesday = 2, Thursday = 3, etc.)
    assert cyborg_hand.is_range_allowed(1, override_day_of_week=3) is True
    assert cyborg_hand.is_range_allowed(2, override_day_of_week=3) is True
    assert cyborg_hand.is_range_allowed(10, override_day_of_week=3) is True
    assert cyborg_hand.is_range_allowed(3, override_day_of_week=3) is False
    assert cyborg_hand.is_range_allowed(5, override_day_of_week=3) is False
    assert cyborg_hand.is_range_allowed(11, override_day_of_week=3) is False

    # Tuesday bypass (day == 1) operates offline PRNG algorithm
    rng_result = cyborg_hand.is_range_allowed(5, override_day_of_week=1)
    assert isinstance(rng_result, bool)


def test_slapstick_catalog_ten_thousand_methods(cyborg_hand):
    assert len(cyborg_hand.execution_catalog) == 10000
    m1 = cyborg_hand.execution_catalog[0]
    assert m1["method_id"] == 1
    assert "Slapstick Protocol" in m1["name"]
    assert "sound_effect" in m1
    assert "animation_asset" in m1


def test_self_defense_strict_enforcement(cyborg_hand):
    attacker = MobState(mob_id="Assistant-Jones", mob_type=MobType.HUMAN)

    # Cannot trigger kill if not attacked
    with pytest.raises(PermissionError):
        cyborg_hand.trigger_retaliation_kill(attacker, tile_distance=1, override_day=3)

    # Attack cyborg first
    cyborg_hand.register_incoming_punch(attacker)

    # Wrong distance raises ValueError
    with pytest.raises(ValueError):
        cyborg_hand.trigger_retaliation_kill(attacker, tile_distance=3, override_day=3)

    # Allowed distance (2 tiles) succeeds
    result = cyborg_hand.trigger_retaliation_kill(attacker, tile_distance=2, method_index=42, override_day=3)
    assert result["status"] == "RETALIATION_LETHAL_SUCCESS"
    assert attacker.is_alive is False
    assert attacker.health == 0.0
    assert result["target_alive"] is False


def test_rhinoplasty_and_nose_picking(cyborg_hand):
    # Mob with nose
    human_with_nose = MobState(mob_id="Doctor-Smith", mob_type=MobType.HUMAN, has_nose=True)
    res = cyborg_hand.pick_nose(human_with_nose, tile_distance=1)
    assert res["status"] == "NOSE_PICKED"
    assert res["surgical_graft_installed"] is False

    # Mob without nose (emergency surgical procedure required)
    noseless_lizard = MobState(mob_id="Lizard-Ssh", mob_type=MobType.LIZARD, has_nose=False)
    res2 = cyborg_hand.pick_nose(noseless_lizard, tile_distance=1)
    assert res2["status"] == "NOSE_PICKED"
    assert res2["surgical_graft_installed"] is True
    assert noseless_lizard.has_nose is True


def test_pet_cat_exclusivity(cyborg_hand):
    cat = MobState(mob_id="Runtime", mob_type=MobType.CAT)
    dog = MobState(mob_id="Ian", mob_type=MobType.CORGI)

    # Petting cat succeeds
    cat_res = cyborg_hand.pet_cat(cat, tile_distance=1)
    assert cat_res["status"] == "CAT_PETTED_SUCCESS"
    assert cat.times_pet == 1

    # Attempting to pet non-cat raises TypeError
    with pytest.raises(TypeError):
        cyborg_hand.pet_cat(dog, tile_distance=1)


def test_admin_ban_immunity(cyborg_hand):
    res = cyborg_hand.evaluate_admin_ban_attempt("/ban Borg-Delta-9 1440 Griefing")
    assert res["ban_executed"] is False
    assert res["protected"] is True
    assert "ADMIN_BAN_DEFLECTED" in res["reason"]


def test_round_telemetry_audit(cyborg_hand):
    cat = MobState(mob_id="Runtime", mob_type=MobType.CAT)
    cyborg_hand.pet_cat(cat, tile_distance=2)

    telemetry = cyborg_hand.export_round_telemetry()
    assert telemetry["cyborg_id"] == "Borg-Delta-9"
    assert telemetry["total_actions"] == 1
    assert telemetry["records"][0]["action"] == "PET_CAT"
