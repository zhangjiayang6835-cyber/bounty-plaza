"""Unit test suite for SS13 Security Weapons Rebalance Subsystem.
Verifies stun baton charge limits, anti-perma-stun diminishing returns, disabler carbine stamina drain,
flashbang area-of-effect calculations, riot shield damage mitigation, beanbag shotgun knockdown,
capacitor recharge rates, DMM map definitions, and DreamMaker syntax exports.
Resolves Issue #595 ($150 USD).
"""

import pytest
from scripts.ss13_security_weapons_rebalance import (
    SS13SecurityWeaponsRebalanceEngine,
    WeaponType,
    TargetMobState
)


@pytest.fixture
def weapons_engine():
    return SS13SecurityWeaponsRebalanceEngine()


def test_stun_baton_charges_and_anti_perma_stun(weapons_engine):
    # Register target clown
    weapons_engine.register_mob("clown_target")

    # Strike 1: full charges available
    res1 = weapons_engine.attack_with_stun_baton("officer_bob", "clown_target", current_time_s=100.0)
    assert res1["charges_left"] == 4
    assert res1["stun_applied_s"] == 4.0
    assert res1["target_stamina_damage"] == 45.0

    # Strike 2 within 2 seconds (anti-perma-stun should trigger, cutting duration to 2.0s)
    res2 = weapons_engine.attack_with_stun_baton("officer_bob", "clown_target", current_time_s=101.5)
    assert res2["charges_left"] == 3
    assert res2["stun_applied_s"] == 2.0
    assert res2["target_stamina_damage"] == 90.0
    assert res2["target_knocked_down"] is True

    # Deplete remaining 3 charges
    weapons_engine.attack_with_stun_baton("officer_bob", "clown_target", current_time_s=110.0)
    weapons_engine.attack_with_stun_baton("officer_bob", "clown_target", current_time_s=120.0)
    res5 = weapons_engine.attack_with_stun_baton("officer_bob", "clown_target", current_time_s=130.0)
    assert res5["charges_left"] == 0

    # 6th strike with depleted capacitor must fail
    res6 = weapons_engine.attack_with_stun_baton("officer_bob", "clown_target", current_time_s=131.0)
    assert res6["success"] is False
    assert res6["reason"] == "BATON_CAPACITOR_DEPLETED"


def test_disabler_carbine_non_lethal_stamina(weapons_engine):
    weapons_engine.register_mob("suspect_alice")

    # Shot at 4 tiles distance (within range 7)
    res = weapons_engine.fire_disabler_carbine("officer_bob", "suspect_alice", distance_tiles=4)
    assert res["success"] is True
    assert res["stamina_damage_dealt"] == 35.0
    assert res["charges_left"] == 19
    # Brute damage should remain 0
    assert weapons_engine.mob_states["suspect_alice"].brute_damage_taken == 0.0

    # Out of range test (8 tiles > 7 max range)
    res_oor = weapons_engine.fire_disabler_carbine("officer_bob", "suspect_alice", distance_tiles=8)
    assert res_oor["success"] is False
    assert res_oor["reason"] == "OUT_OF_RANGE"


def test_flashbang_acoustic_detonation(weapons_engine):
    targets = [
        ("nearby_greytide", 10, 11),   # 1 tile away
        ("mid_distance_chef", 10, 14), # 4 tiles away
        ("far_away_captain", 10, 25),  # 15 tiles away (out of 7 range)
    ]

    results = weapons_engine.detonate_flashbang(epicenter_x=10, epicenter_y=10, targets=targets)
    assert len(results) == 2  # Only 2 within 7 tiles

    nearby = next(r for r in results if r["ckey"] == "nearby_greytide")
    mid = next(r for r in results if r["ckey"] == "mid_distance_chef")

    assert nearby["distance"] == 1.0
    assert nearby["flash_duration_s"] > mid["flash_duration_s"]
    assert nearby["stamina_damage"] > mid["stamina_damage"]


def test_riot_shield_damage_mitigation(weapons_engine):
    res = weapons_engine.apply_riot_shield_defense("officer_shield", incoming_damage=50.0)
    assert res["block_chance"] == 0.60
    assert res["incoming_damage"] == 50.0
    # 70% of 50.0 = 35.0 blocked
    assert res["damage_absorbed_by_shield"] == 35.0
    # 30% of 50.0 = 15.0 passed through
    assert res["damage_passed_to_defender"] == 15.0
    assert res["slowdown_factor"] == 1.5


def test_beanbag_shotgun_knockdown(weapons_engine):
    res = weapons_engine.fire_beanbag_shotgun("officer_shotgun", "rampaging_assistant", distance_tiles=3)
    assert res["success"] is True
    assert res["brute_dealt"] == 8.0
    assert res["stamina_dealt"] == 60.0
    assert res["target_knocked_down"] is True
    assert res["charges_left"] == 5


def test_capacitor_recharge_rates(weapons_engine):
    # Deplete 2 charges from stun baton
    weapons_engine.attack_with_stun_baton("officer_bob", "target", current_time_s=10.0)
    weapons_engine.attack_with_stun_baton("officer_bob", "target", current_time_s=12.0)
    assert weapons_engine.weapons_registry[WeaponType.STUN_BATON].current_charges == 3

    # Elapsed 12 seconds = 2 charges recharged (6s per charge)
    recharge_res = weapons_engine.recharge_capacitors(elapsed_seconds=12.5)
    assert recharge_res[WeaponType.STUN_BATON] == 5


def test_dmm_map_and_dreammaker_exports(weapons_engine):
    dmm_dict = weapons_engine.export_map_integration_dmm()
    assert "IceBoxStation.dmm" in dmm_dict
    assert "/obj/item/melee/baton/rebalanced" in dmm_dict["IceBoxStation.dmm"]
    assert "/obj/item/gun/energy/disabler/carbine" in dmm_dict["IceBoxStation.dmm"]

    dm_code = weapons_engine.export_dreammaker_code()
    assert "/obj/item/melee/baton/rebalanced" in dm_code
    assert "/obj/item/gun/energy/disabler/carbine" in dm_code
    assert "/obj/item/shield/riot/polycarb" in dm_code
