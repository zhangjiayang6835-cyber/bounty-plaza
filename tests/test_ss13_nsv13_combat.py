"""Unit tests for NSV13 Space Battleship & Naval Combat subsystem.
Resolves Issue #607: [BOUNTY] [EASY AI TASK] [$40] [AGENTIC] [AGENT READY][PAID BOUNTY] [UNCLAIMED] Port NSV13.
All comments and specifications comply with catgirl speech ending in -nya! -nya
"""

import pytest
from scripts.ss13_nsv13_combat import (
    MunitionsDepartment,
    MunitionType,
    MultiZExplosionManager,
    OvermapTreadmill,
    PixelHitboxCalculator,
    AuxmosSystem,
    Skynet2CombatShip,
    StarSystemManager,
    EnergyShieldSystem,
    ArmorWellSystem,
    FighterSquadron,
    NSV13WarshipEngine,
    ShipAlertLevel,
)


def test_munitions_department_loading_and_firing():
    # Test autoloaders and firing heavy tungsten munitions -nya
    dept = MunitionsDepartment()
    res = dept.load_and_fire(MunitionType.HEAVY_KINETIC, tubes=2)
    assert res["status"] == "FIRED"
    assert res["remaining_shells"] == 38
    assert res["munition"] == "heavy_kinetic"

    # Test out of ammunition error handling -nya
    with pytest.raises(ValueError, match="Insufficient"):
        dept.load_and_fire(MunitionType.PLASMA_TORPEDO, tubes=100)


def test_multi_z_explosion_propagation():
    # Test shockwave propagation through multi-deck hull plating -nya
    blast = MultiZExplosionManager.propagate_blast(center_coord=(100, 100, 2), yield_megatons=30.0)
    assert len(blast) == 3
    deck_2 = next(b for b in blast if b["target_z"] == 2)
    deck_1 = next(b for b in blast if b["target_z"] == 1)

    assert deck_2["attenuated_yield"] == 30.0
    assert deck_2["hull_punctured"] is True
    assert deck_1["attenuated_yield"] < 30.0


def test_overmap_treadmill_movement():
    # Test celestial coordinate update during cruiser transit -nya
    overmap = OvermapTreadmill(ship_overmap_coord=(100.0, 200.0), velocity_vector=(10.0, 5.0))
    new_coord = overmap.advance_step(delta_time_s=2.0)
    assert new_coord == (120.0, 210.0)


def test_pixel_hitbox_collision():
    # Test sub-tile pixel bounding box intersection -nya
    box_a = (10.0, 10.0, 30.0, 30.0)
    box_b = (25.0, 25.0, 45.0, 45.0)
    box_c = (50.0, 50.0, 70.0, 70.0)

    assert PixelHitboxCalculator.check_collision(box_a, box_b) is True
    assert PixelHitboxCalculator.check_collision(box_a, box_c) is False


def test_auxmos_hull_breach_containment():
    # Test emergency atmospheric compartmentalization -nya
    aux = AuxmosSystem()
    res = aux.trigger_hull_breach_protocol()
    assert res["status"] == "BREACH_CONTAINED"
    assert aux.blast_doors_sealed is True
    assert aux.emergency_scrubbers_active is True
    assert aux.nitrogen_reserves_kpa < 5000.0


def test_skynet2_combat_ship():
    # Test hostile NPC combat vessel targeting -nya
    skynet = Skynet2CombatShip()
    res = skynet.acquire_target_and_engage("NSV-Forefighter")
    assert res["action"] == "ENGAGING_TARGET"
    assert res["salvo_damage"] == 180.0
    assert skynet.locked_target == "NSV-Forefighter"


def test_starsystem_navigation_and_warp():
    # Test starmap navigation and warp jump points -nya
    starmap = StarSystemManager()
    res = starmap.initiate_warp_jump("JumpPoint-Sol")
    assert res["status"] == "WARP_JUMP_SUCCESSFUL"
    assert res["destination"] == "JumpPoint-Sol"

    with pytest.raises(ValueError, match="Unknown warp jump point"):
        starmap.initiate_warp_jump("JumpPoint-Nonexistent")


def test_energy_shield_and_armor_well_defense():
    # Test shield absorption and armor damage mitigation -nya
    shields = EnergyShieldSystem(max_capacity_mj=500.0, current_shield_mj=500.0)
    armor = ArmorWellSystem()

    bleedthrough = shields.absorb_damage(650.0)
    assert bleedthrough == 150.0
    assert shields.current_shield_mj == 0.0

    hit_res = armor.take_hit("port", bleedthrough)
    assert hit_res["quadrant"] == "port"
    assert hit_res["is_breached"] is False
    assert armor.plating_integrity["port"] < 400.0


def test_fighter_squadron_sortie():
    # Test carrier fighter launch protocol -nya
    squadron = FighterSquadron(active_fighters=8)
    res = squadron.launch_strike_wing(targets_count=4)
    assert res["squadron_status"] == "SORTIE_LAUNCHED"
    assert res["fighters_deployed"] == 4


def test_nsv13_warship_engine_and_shakedown_gamemode():
    # Test complete warship orchestrator and shakedown drill -nya
    warship = NSV13WarshipEngine()
    res = warship.execute_shakedown_trial("meteor_storm_evasion")
    assert res["mode"] == "SHAKEDOWN_GAMEMODE"
    assert warship.alert_level == ShipAlertLevel.SHAKEDOWN

    dm_defs = warship.export_dreammaker_definitions()
    assert "/datum/nsv_ship_controller" in dm_defs
    assert "/obj/machinery/munitions/cannon_loader" in dm_defs
