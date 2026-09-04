"""Unit test suite for SS13 Mecha Units Overhaul Subsystem.
Verifies thermal generation, passive and radiator-assisted dissipation, safety shutoffs,
overclock penalties, pilot cockpit burn calculations, modular complexity budgets,
MMI/positronic combat piloting lockouts, direct component AP damage, AI beacon hacking gates,
dedicated melee vs default punches, DMM map additions, and DreamMaker syntax exports.
Resolves Issue #611 ($500 USD).
"""

import pytest
from scripts.ss13_mecha_units_overhaul import (
    SS13MechaUnitsOverhaulEngine,
    MechaChassisType,
    PilotType,
    MechaEquipmentType,
    EquipmentModule,
    MechaPartTiers
)


@pytest.fixture
def mecha_engine():
    return SS13MechaUnitsOverhaulEngine()


def test_modular_complexity_capacity_pool(mecha_engine):
    # Ripley has capacity 12
    ripley = mecha_engine.create_mecha("ripley_01", MechaChassisType.RIPLEY)
    assert ripley.max_complexity == 12
    assert ripley.used_complexity == 0

    claw = EquipmentModule(
        module_type=MechaEquipmentType.HYDRAULIC_CLAW,
        name="Hydraulic Clamp",
        complexity_cost=5,
        heat_generated_per_use=10.0,
        power_draw_per_use=50.0
    )
    res_claw = mecha_engine.install_module("ripley_01", claw)
    assert res_claw["success"] is True
    assert res_claw["used_complexity"] == 5
    assert res_claw["remaining_complexity"] == 7

    drill = EquipmentModule(
        module_type=MechaEquipmentType.PNEUMATIC_JACKHAMMER,
        name="Jackhammer Drill",
        complexity_cost=6,
        heat_generated_per_use=12.0,
        power_draw_per_use=60.0
    )
    res_drill = mecha_engine.install_module("ripley_01", drill)
    assert res_drill["success"] is True
    assert res_drill["used_complexity"] == 11
    assert res_drill["remaining_complexity"] == 1

    # Over capacity module (cost 3 > remaining 1)
    heavy_gun = EquipmentModule(
        module_type=MechaEquipmentType.BALLISTIC_CANNON,
        name="Heavy Cannon",
        complexity_cost=3,
        heat_generated_per_use=20.0,
        power_draw_per_use=100.0
    )
    res_gun = mecha_engine.install_module("ripley_01", heavy_gun)
    assert res_gun["success"] is False
    assert res_gun["reason"] == "EXCEEDS_COMPLEXITY_CAPACITY"


def test_thermal_strafing_and_servo_mitigation(mecha_engine):
    # Standard Tier 1 servo mech
    mecha_engine.create_mecha("mech_t1", MechaChassisType.GYGAX, servo_tier=1)
    # Tier 3 servo mech
    mecha_engine.create_mecha("mech_t3", MechaChassisType.GYGAX, servo_tier=3)

    res_t1 = mecha_engine.execute_strafe_movement("mech_t1")
    res_t3 = mecha_engine.execute_strafe_movement("mech_t3")

    assert res_t1["heat_added_k"] == 15.0
    assert res_t3["heat_added_k"] < res_t1["heat_added_k"]  # Servo mitigation lowers heat


def test_thermal_safety_shutdown_and_overclocking(mecha_engine):
    durand = mecha_engine.create_mecha("durand_test", MechaChassisType.DURAND)
    laser = EquipmentModule(
        module_type=MechaEquipmentType.ENERGY_LASER_BURST,
        name="Burst Laser",
        complexity_cost=4,
        heat_generated_per_use=35.0,
        power_draw_per_use=80.0
    )
    mecha_engine.install_module("durand_test", laser)

    # Fire laser repeatedly to cross default threshold (380 K)
    for _ in range(3):
        mecha_engine.activate_module("durand_test", "Burst Laser")

    assert durand.internal_temp_k >= 380.0
    assert durand.safety_shutdown_engaged is True

    # 4th shot should be blocked by safety system
    blocked = mecha_engine.activate_module("durand_test", "Burst Laser")
    assert blocked["success"] is False
    assert blocked["reason"] == "SAFETY_THERMAL_SHUTDOWN_ENGAGED"

    # Overclock safety override
    mecha_engine.toggle_overclock("durand_test", True)
    assert durand.is_safety_overclocked is True
    assert durand.safety_shutdown_engaged is False

    # Now module can fire despite exceeding safety threshold
    overclocked_shot = mecha_engine.activate_module("durand_test", "Burst Laser")
    assert overclocked_shot["success"] is True


def test_radiator_fan_accelerated_dissipation(mecha_engine):
    # Mech A without radiator, Mech B with cargo radiator
    mecha_engine.create_mecha("mech_no_fan", MechaChassisType.RIPLEY)
    mecha_engine.create_mecha("mech_fan", MechaChassisType.RIPLEY)

    fan = EquipmentModule(
        module_type=MechaEquipmentType.CARGO_RADIATOR_FAN,
        name="Cargo Radiator Fan",
        complexity_cost=2,
        heat_generated_per_use=0.0,
        power_draw_per_use=10.0
    )
    mecha_engine.install_module("mech_fan", fan)

    # Set both mechs to 350 K with 293 K ambient
    mecha_engine.active_mechas["mech_no_fan"].internal_temp_k = 350.0
    mecha_engine.active_mechas["mech_fan"].internal_temp_k = 350.0

    res_no_fan = mecha_engine.passive_heat_dissipation("mech_no_fan", elapsed_seconds=10.0)
    res_fan = mecha_engine.passive_heat_dissipation("mech_fan", elapsed_seconds=10.0)

    assert res_fan["heat_lost_k"] > res_no_fan["heat_lost_k"]
    # 3.5x cooling multiplier
    assert abs(res_fan["heat_lost_k"] - (res_no_fan["heat_lost_k"] * 3.5)) < 0.1


def test_emergency_overheat_penalties_and_pilot_burn(mecha_engine):
    mecha = mecha_engine.create_mecha("hot_mech", MechaChassisType.MARAUDER)
    mecha_engine.assign_pilot("hot_mech", "pilot_bob", PilotType.ORGANIC_HUMAN, has_heat_insulating_gear=False)

    # Force heat past emergency threshold (460 K)
    mecha.internal_temp_k = 500.0
    mecha_engine._evaluate_thermal_safety(mecha)

    # Movement speed and armor stability degraded
    assert mecha.movement_speed_factor < 1.0
    assert mecha.armor_stability < 100.0

    # Uninsulated pilot burns in closed cockpit
    burn_res = mecha_engine.check_pilot_heat_damage("hot_mech")
    assert burn_res["burn_damage"] > 0.0
    assert burn_res["warning"] == "PILOT_BURNING_IN_OVERHEATED_COCKPIT"

    # Insulated gear negates burns
    mecha.pilot_has_heat_gear = True
    burn_gear = mecha_engine.check_pilot_heat_damage("hot_mech")
    assert burn_gear["burn_damage"] == 0.0
    assert burn_gear["reason"] == "INSULATED_GEAR_EQUIPPED"


def test_mmi_positronic_combat_pilot_restriction(mecha_engine):
    mecha_engine.create_mecha("combat_durand", MechaChassisType.DURAND)
    mecha_engine.create_mecha("utility_ripley", MechaChassisType.RIPLEY)

    # MMI cannot pilot combat Durand
    res_mmi_combat = mecha_engine.assign_pilot("combat_durand", "mmi_brain", PilotType.MMI)
    assert res_mmi_combat["success"] is False
    assert res_mmi_combat["reason"] == "MMI_POSITRONIC_COMBAT_PILOT_PROHIBITED"

    # Positronic cannot pilot combat Marauder
    res_pos_combat = mecha_engine.assign_pilot("combat_durand", "pos_brain", PilotType.POSITRONIC_BRAIN)
    assert res_pos_combat["success"] is False

    # MMI can pilot utility Ripley
    res_mmi_utility = mecha_engine.assign_pilot("utility_ripley", "mmi_brain", PilotType.MMI)
    assert res_mmi_utility["success"] is True


def test_armor_piercing_direct_component_damage(mecha_engine):
    mecha = mecha_engine.create_mecha("target_mech", MechaChassisType.GYGAX)
    claw = EquipmentModule(
        module_type=MechaEquipmentType.HYDRAULIC_CLAW,
        name="Front Claw",
        complexity_cost=4,
        heat_generated_per_use=5.0,
        power_draw_per_use=20.0
    )
    mecha_engine.install_module("target_mech", claw)

    # AP strike on battery
    res_bat = mecha_engine.apply_armor_piercing_hit("target_mech", incoming_damage=30.0, target_component="battery")
    assert res_bat["struck"] == "battery"
    assert mecha.battery_integrity == 70.0

    # AP strike directly on installed module
    res_mod = mecha_engine.apply_armor_piercing_hit("target_mech", incoming_damage=40.0, target_component="Front Claw")
    assert res_mod["struck"] == "Front Claw"
    assert claw.integrity == 60.0


def test_visibility_rear_mirror_and_ai_beacon_hacking(mecha_engine):
    mecha = mecha_engine.create_mecha("blind_mech", MechaChassisType.RIPLEY)
    assert mecha.field_of_view_deg == 120.0

    # AI tries to hack without beacon -> rejected
    ai_hack_fail = mecha_engine.attempt_ai_remote_hack("blind_mech", "malf_ai")
    assert ai_hack_fail["success"] is False
    assert ai_hack_fail["reason"] == "NO_BEACON_INSTALLED_HACK_REJECTED"

    # Add rear-view mirror from cargo (+60 FOV)
    mirror = EquipmentModule(
        module_type=MechaEquipmentType.IMPROVISED_REAR_MIRROR,
        name="Improvised Mirror",
        complexity_cost=1,
        heat_generated_per_use=0.0,
        power_draw_per_use=0.0
    )
    mecha_engine.install_module("blind_mech", mirror)
    assert mecha.field_of_view_deg == 180.0

    # Mount optical camera beacon -> grants 360 view but exposes to AI hack
    beacon = EquipmentModule(
        module_type=MechaEquipmentType.CAMERA_BEACON,
        name="Optical Camera Beacon",
        complexity_cost=2,
        heat_generated_per_use=0.0,
        power_draw_per_use=15.0
    )
    mecha_engine.install_module("blind_mech", beacon)
    assert mecha.field_of_view_deg == 360.0

    # Now AI hack succeeds
    ai_hack_success = mecha_engine.attempt_ai_remote_hack("blind_mech", "malf_ai")
    assert ai_hack_success["success"] is True
    assert mecha.is_ai_hacked is True


def test_dedicated_melee_weapons_vs_default_punch(mecha_engine):
    mecha_engine.create_mecha("melee_mech", MechaChassisType.DURAND)

    # Without blade: weak default hydraulic punch
    punch_res = mecha_engine.execute_dedicated_melee_attack("melee_mech", "reinforced_wall", is_structure_or_vehicle=True)
    assert punch_res["weapon"] == "default_hydraulic_punch"
    assert punch_res["damage_dealt"] == 12.0
    assert punch_res["armor_penetration"] == 5.0

    # Install dedicated demolition blade
    blade = EquipmentModule(
        module_type=MechaEquipmentType.DEDICATED_MELEE_BLADE,
        name="Vibro Demolition Blade",
        complexity_cost=4,
        heat_generated_per_use=10.0,
        power_draw_per_use=40.0,
        armor_penetration=35.0,
        demolition_damage=50.0
    )
    mecha_engine.install_module("melee_mech", blade)

    blade_res = mecha_engine.execute_dedicated_melee_attack("melee_mech", "reinforced_wall", is_structure_or_vehicle=True)
    assert blade_res["weapon"] == "Vibro Demolition Blade"
    assert blade_res["damage_dealt"] == 95.0  # 45 base + 50 demolition bonus
    assert blade_res["armor_penetration"] == 35.0


def test_dmm_and_dreammaker_exports(mecha_engine):
    dmm_dict = mecha_engine.export_map_integration_dmm()
    assert "IceBoxStation.dmm" in dmm_dict
    assert "/obj/mecha/combat/durand/overhauled" in dmm_dict["IceBoxStation.dmm"]
    assert "/obj/item/mecha_parts/radiator_fan" in dmm_dict["IceBoxStation.dmm"]

    dm_code = mecha_engine.export_dreammaker_code()
    assert "/obj/mecha" in dm_code
    assert "handle_heat_dissipation" in dm_code
    assert "can_ai_hack" in dm_code
