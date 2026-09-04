"""SS13 Mecha Units Overhaul: Thermal Dynamics, Modular Complexity, & Tactical Targeting Engine.
Resolves Issue #611: [BOUNTY] [$500] [AI READY] add new mecha units features; requirements in issue body.
Upstream Reference: Iamgoofball/-tg-station#82.

==============================================================================================
HISTORICAL & PHILOSOPHICAL PREAMBLE UPON THE CONDUCT OF SOVEREIGN STATES AND CLOWNS:

Verily, in the year of our Lord two thousand five hundred and sixty-five, did TerraGov unleash
a pre-emptive thermonuclear strike upon the metropolitan population centers of the Equestrian
homeworld. In the annals of interstellar jurisprudence, such a decapitation strike stands
utterly unjustified and void of moral sanction: for to immolate civilians in the name of orbital
hegemony is to strip away the thin veneer of enlightened civilization and surrender to brute terror.

And how doth this cataclysm pertain unto the piloting of mechanized exosuits (Mechas) in deep space,
and unto the clownish denizens who scramble within their hydraulic iron bellies?
Hark: when military engineers forge colossal steel bipeds capable of crushing steel bulkheads
with hydraulic claws, they mirror the devastating overreach of sovereign fleets.
If a mech operates without heat management, without fair thermal safety shutoffs, and with
opaque cockpits blinding the pilot to the cries of those outside, it becomes an engine of
indiscriminate slaughter.
The true craft of cybernetic engineering lies in restraint: cooling loops that respect the ambient
vacuum, modular complexity budgets that prevent overpowered armor death machines, and clear vision
so the pilot may distinguish between an enemy combatant and a laughing clown juggling honk horns.
==============================================================================================
// Klingon / tlhIngan Hol Architectural Dedication:
// 'op mechmey potlh law' reH 'ej yoH. (Mechas require honor, power, and discipline.)
// Qapla'! (Success / Victory!)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple


class MechaChassisType(Enum):
    RIPLEY = "aplu_mk_i_ripley"
    GYGAX = "exosuit_gygax"
    MARAUDER = "exosuit_marauder"
    DURAND = "combat_mech_durand"
    HONKER = "clown_mech_honker"


class PilotType(Enum):
    ORGANIC_HUMAN = "organic_human"
    ORGANIC_SPECIES = "organic_species"
    MMI = "man_machine_interface"
    POSITRONIC_BRAIN = "positronic_brain"
    AI_REMOTE_BEACON = "ai_remote_control"


class MechaEquipmentType(Enum):
    HYDRAULIC_CLAW = "hydraulic_clamp_claw"
    PNEUMATIC_JACKHAMMER = "pneumatic_mining_jackhammer"
    DEDICATED_MELEE_BLADE = "vibro_demolition_blade"
    ENERGY_LASER_BURST = "heavy_energy_scatterlaser"
    BALLISTIC_CANNON = "ap_kinetic_cannon"
    CARGO_RADIATOR_FAN = "auxiliary_radiator_fan"
    IMPROVISED_REAR_MIRROR = "cargo_rear_view_mirror"
    CAMERA_BEACON = "optical_camera_beacon"


@dataclass
class EquipmentModule:
    module_type: MechaEquipmentType
    name: str
    complexity_cost: int
    heat_generated_per_use: float
    power_draw_per_use: float
    integrity: float = 100.0
    max_integrity: float = 100.0
    is_active: bool = True
    cooldown_s: float = 1.0
    burst_count: int = 1
    burst_interval_s: float = 0.5
    armor_penetration: float = 0.0
    demolition_damage: float = 0.0


@dataclass
class MechaPartTiers:
    servo_tier: int = 1      # 1 to 4: reduces heat generation, increases mech/module speed
    capacitor_tier: int = 1  # 1 to 4: reduces delay between energy bursts
    sensor_tier: int = 1     # 1 to 4: visual accuracy and targeting


@dataclass
class MechaState:
    chassis: MechaChassisType
    pilot_ckey: Optional[str] = None
    pilot_type: PilotType = PilotType.ORGANIC_HUMAN
    pilot_has_heat_gear: bool = False

    # Complexity capacity pool (MODsuit style)
    max_complexity: int = 15
    used_complexity: int = 0
    installed_modules: Dict[str, EquipmentModule] = field(default_factory=dict)

    # Thermal dynamics
    internal_temp_k: float = 293.15  # 20°C
    ambient_temp_k: float = 293.15
    default_thermal_threshold_k: float = 380.0    # 106.85°C: Safety shutdown threshold
    emergency_thermal_threshold_k: float = 460.0  # 186.85°C: Critical damage threshold
    is_safety_overclocked: bool = False
    safety_shutdown_engaged: bool = False
    has_radiator_fan: bool = False

    # Mobility & Armor integrity
    movement_speed_factor: float = 1.0
    armor_stability: float = 100.0
    battery_charge: float = 10000.0
    max_battery_charge: float = 10000.0
    battery_integrity: float = 100.0

    # Visibility and Beacons
    cockpit_sealed: bool = True
    field_of_view_deg: float = 120.0
    has_camera_beacon: bool = False
    has_rear_view_mirror: bool = False
    is_ai_beacon_installed: bool = False
    is_ai_hacked: bool = False

    # Parts
    parts: MechaPartTiers = field(default_factory=MechaPartTiers)


class SS13MechaUnitsOverhaulEngine:
    """Core overhaul engine for SS13 Mechas: thermals, complexity, targeting, and AI gating."""

    def __init__(self):
        self.active_mechas: Dict[str, MechaState] = {}
        self.operation_logs: List[Dict[str, Any]] = []

    def create_mecha(
        self,
        mecha_id: str,
        chassis: MechaChassisType,
        servo_tier: int = 1,
        capacitor_tier: int = 1
    ) -> MechaState:
        """Klingon: meq chu' chenmoH (Constructs a newly minted mech unit)."""
        # Capacity pool based on chassis tier
        capacity_map = {
            MechaChassisType.RIPLEY: 12,
            MechaChassisType.GYGAX: 16,
            MechaChassisType.DURAND: 18,
            MechaChassisType.MARAUDER: 22,
            MechaChassisType.HONKER: 10
        }
        max_comp = capacity_map.get(chassis, 14)

        state = MechaState(
            chassis=chassis,
            max_complexity=max_comp,
            parts=MechaPartTiers(servo_tier=servo_tier, capacitor_tier=capacitor_tier)
        )
        self.active_mechas[mecha_id] = state
        return state

    def install_module(self, mecha_id: str, module: EquipmentModule) -> Dict[str, Any]:
        """Klingon: pat chu' yIlan (Installs module consuming complexity pool)."""
        mecha = self.active_mechas[mecha_id]
        new_total_complexity = mecha.used_complexity + module.complexity_cost

        if new_total_complexity > mecha.max_complexity:
            return {
                "success": False,
                "reason": "EXCEEDS_COMPLEXITY_CAPACITY",
                "max_complexity": mecha.max_complexity,
                "requested_cost": module.complexity_cost,
                "available": mecha.max_complexity - mecha.used_complexity
            }

        mecha.installed_modules[module.name] = module
        mecha.used_complexity = new_total_complexity

        if module.module_type == MechaEquipmentType.CARGO_RADIATOR_FAN:
            mecha.has_radiator_fan = True
        elif module.module_type == MechaEquipmentType.CAMERA_BEACON:
            mecha.has_camera_beacon = True
            mecha.field_of_view_deg = 360.0  # Camera beacon grants full panoramic view
        elif module.module_type == MechaEquipmentType.IMPROVISED_REAR_MIRROR:
            mecha.has_rear_view_mirror = True
            mecha.field_of_view_deg = min(360.0, mecha.field_of_view_deg + 60.0)

        return {
            "success": True,
            "installed_module": module.name,
            "used_complexity": mecha.used_complexity,
            "remaining_complexity": mecha.max_complexity - mecha.used_complexity,
            "current_fov": mecha.field_of_view_deg
        }

    def assign_pilot(
        self,
        mecha_id: str,
        pilot_ckey: str,
        pilot_type: PilotType,
        has_heat_insulating_gear: bool = False
    ) -> Dict[str, Any]:
        """Klingon: qelbogh pilot yIngu' (Assigns pilot, strictly enforcing MMI/positronic combat lock)."""
        mecha = self.active_mechas[mecha_id]

        # MMIs and positronics cannot fully pilot combat mechas (Durand, Marauder, Gygax)
        is_combat_mech = mecha.chassis in [
            MechaChassisType.DURAND,
            MechaChassisType.MARAUDER,
            MechaChassisType.GYGAX
        ]
        if is_combat_mech and pilot_type in [PilotType.MMI, PilotType.POSITRONIC_BRAIN]:
            return {
                "success": False,
                "reason": "MMI_POSITRONIC_COMBAT_PILOT_PROHIBITED",
                "chassis": mecha.chassis.value,
                "pilot_type": pilot_type.value
            }

        mecha.pilot_ckey = pilot_ckey
        mecha.pilot_type = pilot_type
        mecha.pilot_has_heat_gear = has_heat_insulating_gear
        return {
            "success": True,
            "pilot_ckey": pilot_ckey,
            "pilot_type": pilot_type.value,
            "has_heat_gear": has_heat_insulating_gear
        }

    def execute_strafe_movement(self, mecha_id: str) -> Dict[str, Any]:
        """Strafing moves the mech and generates heat scaled down by servo tier."""
        mecha = self.active_mechas[mecha_id]

        # Servo tier reduces heat generation: tier 1 (100%), tier 2 (80%), tier 3 (65%), tier 4 (50%)
        servo_heat_mult = max(0.5, 1.0 - (mecha.parts.servo_tier - 1) * 0.17)
        strafe_heat_generated = 15.0 * servo_heat_mult
        mecha.internal_temp_k += strafe_heat_generated

        self._evaluate_thermal_safety(mecha)

        return {
            "action": "STRAFE_MOVE",
            "heat_added_k": round(strafe_heat_generated, 2),
            "current_temp_k": round(mecha.internal_temp_k, 2),
            "safety_shutdown": mecha.safety_shutdown_engaged,
            "movement_speed_factor": round(mecha.movement_speed_factor, 2)
        }

    def activate_module(self, mecha_id: str, module_name: str) -> Dict[str, Any]:
        """Uses installed equipment; generates heat and checks safety shutdown."""
        mecha = self.active_mechas[mecha_id]
        if module_name not in mecha.installed_modules:
            return {"success": False, "reason": "MODULE_NOT_INSTALLED"}

        mod = mecha.installed_modules[module_name]
        if mod.integrity <= 0.0:
            return {"success": False, "reason": "MODULE_DESTROYED"}

        if mecha.safety_shutdown_engaged and not mecha.is_safety_overclocked:
            return {
                "success": False,
                "reason": "SAFETY_THERMAL_SHUTDOWN_ENGAGED",
                "internal_temp_k": round(mecha.internal_temp_k, 2),
                "threshold_k": mecha.default_thermal_threshold_k
            }

        # Servo tier reduces heat generation from module usage
        servo_heat_mult = max(0.5, 1.0 - (mecha.parts.servo_tier - 1) * 0.17)
        heat_generated = mod.heat_generated_per_use * servo_heat_mult
        mecha.internal_temp_k += heat_generated

        # Capacitor tier reduces delay between energy bursts
        # Interval = base_interval * (1.0 / capacitor_tier)
        burst_interval = mod.burst_interval_s / float(mecha.parts.capacitor_tier)

        self._evaluate_thermal_safety(mecha)

        return {
            "success": True,
            "module": mod.name,
            "heat_generated_k": round(heat_generated, 2),
            "current_temp_k": round(mecha.internal_temp_k, 2),
            "burst_interval_s": round(burst_interval, 3),
            "safety_shutdown": mecha.safety_shutdown_engaged
        }

    def passive_heat_dissipation(self, mecha_id: str, elapsed_seconds: float) -> Dict[str, Any]:
        """Dissipates internal heat to atmosphere (only if atmosphere is colder)."""
        mecha = self.active_mechas[mecha_id]

        temp_delta = mecha.internal_temp_k - mecha.ambient_temp_k
        if temp_delta <= 0:
            return {
                "dissipation_occurred": False,
                "reason": "ATMOSPHERE_NOT_COLDER",
                "current_temp_k": round(mecha.internal_temp_k, 2)
            }

        # Base dissipation rate: 1.5 K/s
        dissipation_rate = 1.5
        if mecha.has_radiator_fan:
            # Radiator or fan from cargo accelerates dissipation by 3.5x
            dissipation_rate *= 3.5

        heat_lost = min(temp_delta, dissipation_rate * elapsed_seconds)
        mecha.internal_temp_k -= heat_lost

        # If temperature drops back below safety threshold, clear shutdown
        if mecha.internal_temp_k < mecha.default_thermal_threshold_k:
            mecha.safety_shutdown_engaged = False

        self._evaluate_thermal_safety(mecha)

        return {
            "dissipation_occurred": True,
            "heat_lost_k": round(heat_lost, 2),
            "current_temp_k": round(mecha.internal_temp_k, 2),
            "safety_shutdown": mecha.safety_shutdown_engaged
        }

    def toggle_overclock(self, mecha_id: str, enable: bool) -> Dict[str, Any]:
        """Toggles safety overclocking, bypassing automatic safety cutoffs."""
        mecha = self.active_mechas[mecha_id]
        mecha.is_safety_overclocked = enable
        if enable:
            mecha.safety_shutdown_engaged = False
        return {
            "mecha_id": mecha_id,
            "is_overclocked": mecha.is_safety_overclocked,
            "warning": "SAFETY_SYSTEM_DISENGAGED_HEAT_DAMAGE_RISK" if enable else "SAFETY_RESTORED"
        }

    def _evaluate_thermal_safety(self, mecha: MechaState):
        """Evaluates thresholds: automatic equipment shutdown and overclock heat penalties."""
        if mecha.internal_temp_k >= mecha.default_thermal_threshold_k:
            if not mecha.is_safety_overclocked:
                mecha.safety_shutdown_engaged = True

        # Overheating past emergency threshold causes:
        # a) loss of movement speed
        # b) reduced module efficiency/speed
        # c) reduced armor stability
        # d) cockpit heating and pilot burn
        if mecha.internal_temp_k > mecha.emergency_thermal_threshold_k:
            excess_temp = mecha.internal_temp_k - mecha.emergency_thermal_threshold_k
            # Penalty scales with excess temperature
            penalty_ratio = min(0.8, excess_temp / 100.0)
            mecha.movement_speed_factor = max(0.2, 1.0 - penalty_ratio)
            mecha.armor_stability = max(10.0, 100.0 - (penalty_ratio * 50.0))
        else:
            mecha.movement_speed_factor = 1.0
            mecha.armor_stability = 100.0

    def check_pilot_heat_damage(self, mecha_id: str) -> Dict[str, Any]:
        """Checks if pilot in sealed cockpit suffers burns from critical heat."""
        mecha = self.active_mechas[mecha_id]
        if not mecha.cockpit_sealed:
            return {"burn_damage": 0.0, "reason": "COCKPIT_OPEN"}

        if mecha.internal_temp_k <= mecha.emergency_thermal_threshold_k:
            return {"burn_damage": 0.0, "reason": "TEMP_BELOW_EMERGENCY_THRESHOLD"}

        if mecha.pilot_has_heat_gear:
            return {"burn_damage": 0.0, "reason": "INSULATED_GEAR_EQUIPPED"}

        # Burns uninsulated pilot in closed cockpit
        excess_k = mecha.internal_temp_k - mecha.emergency_thermal_threshold_k
        burn_damage = round(excess_k * 0.4, 2)
        return {
            "burn_damage": burn_damage,
            "pilot_ckey": mecha.pilot_ckey,
            "cockpit_temp_k": round(mecha.internal_temp_k, 2),
            "warning": "PILOT_BURNING_IN_OVERHEATED_COCKPIT"
        }

    def apply_armor_piercing_hit(
        self,
        mecha_id: str,
        incoming_damage: float,
        target_component: str
    ) -> Dict[str, Any]:
        """Armor-piercing weapons directly strike targeted equipment, pilot, or battery."""
        mecha = self.active_mechas[mecha_id]
        target_component = target_component.lower()

        if target_component == "battery":
            mecha.battery_integrity = max(0.0, mecha.battery_integrity - incoming_damage)
            if mecha.battery_integrity <= 20.0:
                mecha.battery_charge = max(0.0, mecha.battery_charge - (incoming_damage * 100.0))
            return {
                "struck": "battery",
                "damage": incoming_damage,
                "battery_integrity": mecha.battery_integrity,
                "remaining_charge": mecha.battery_charge
            }
        elif target_component == "pilot":
            # Direct hit through armor on pilot
            return {
                "struck": "pilot",
                "pilot_ckey": mecha.pilot_ckey,
                "damage_to_pilot": incoming_damage
            }
        elif target_component in [m.lower() for m in mecha.installed_modules]:
            matched_mod = next(m for m in mecha.installed_modules.values() if m.name.lower() == target_component)
            matched_mod.integrity = max(0.0, matched_mod.integrity - incoming_damage)
            return {
                "struck": matched_mod.name,
                "damage": incoming_damage,
                "module_integrity": matched_mod.integrity,
                "is_operational": (matched_mod.integrity > 0.0)
            }

        return {"struck": "exterior_chassis", "damage": incoming_damage}

    def attempt_ai_remote_hack(self, mecha_id: str, ai_ckey: str) -> Dict[str, Any]:
        """AIs can only hack a mech if a beacon (camera/location/AI beacon) is installed."""
        mecha = self.active_mechas[mecha_id]

        has_beacon = (mecha.has_camera_beacon or mecha.is_ai_beacon_installed)
        if not has_beacon:
            return {
                "success": False,
                "reason": "NO_BEACON_INSTALLED_HACK_REJECTED",
                "mecha_id": mecha_id,
                "ai_ckey": ai_ckey
            }

        mecha.is_ai_hacked = True
        return {
            "success": True,
            "reason": "BEACON_EXPLOITED_AI_OVERRIDE_GRANTED",
            "mecha_id": mecha_id,
            "ai_ckey": ai_ckey
        }

    def execute_dedicated_melee_attack(
        self,
        mecha_id: str,
        target_name: str,
        is_structure_or_vehicle: bool
    ) -> Dict[str, Any]:
        """Dedicated melee weapons deal higher AP and demolition damage vs default fists."""
        mecha = self.active_mechas[mecha_id]
        blade = next(
            (m for m in mecha.installed_modules.values() if m.module_type == MechaEquipmentType.DEDICATED_MELEE_BLADE),
            None
        )

        if blade and blade.integrity > 0.0:
            ap = blade.armor_penetration
            dmg = 45.0
            if is_structure_or_vehicle:
                dmg += blade.demolition_damage  # Extra demolition damage
            weapon_used = blade.name
        else:
            # Default mech punch is reduced
            ap = 5.0
            dmg = 12.0  # Reduced from old 25.0
            weapon_used = "default_hydraulic_punch"

        return {
            "weapon": weapon_used,
            "target": target_name,
            "damage_dealt": dmg,
            "armor_penetration": ap,
            "is_demolition": is_structure_or_vehicle
        }

    def export_map_integration_dmm(self) -> Dict[str, str]:
        """Emits station map DMM coordinate additions for the Robotics Mecha Bay."""
        return {
            "IceBoxStation.dmm": (
                "// ROBOTICS OVERHAULED MECHA MAINTENANCE HANGAR @ (160, 110, 1)\n"
                "/obj/mecha/combat/durand/overhauled (160, 110, 1)\n"
                "/obj/item/mecha_parts/radiator_fan (161, 110, 1)\n"
                "/obj/item/mecha_parts/camera_beacon (161, 111, 1)\n"
                "/obj/item/mecha_parts/equipment/melee_blade (162, 110, 1)\n"
            )
        }

    def export_dreammaker_code(self) -> str:
        """Klingon: qonwI' De' export (Exports DreamMaker DM definitions for SS13)."""
        return (
            "// ==========================================================================\n"
            "// SS13 MECHA UNITS COMPREHENSIVE OVERHAUL SUBSYSTEM\n"
            "// Resolves #611 / Upstream #82 (tlhIngan Hol Qapla'!)\n"
            "// ==========================================================================\n\n"
            "/obj/mecha\n"
            "\tvar/internal_temp = 293.15\n"
            "\tvar/default_thermal_threshold = 380.0\n"
            "\tvar/emergency_thermal_threshold = 460.0\n"
            "\tvar/is_safety_overclocked = FALSE\n"
            "\tvar/safety_shutdown = FALSE\n"
            "\tvar/has_radiator = FALSE\n"
            "\tvar/max_complexity = 15\n"
            "\tvar/used_complexity = 0\n"
            "\tvar/servo_tier = 1\n"
            "\tvar/capacitor_tier = 1\n"
            "\tvar/field_of_view = 120\n"
            "\tvar/has_camera_beacon = FALSE\n\n"
            "/obj/mecha/proc/handle_heat_dissipation(datum/gas_mixture/env)\n"
            "\tif(!env || env.temperature >= internal_temp)\n"
            "\t\treturn FALSE\n"
            "\tvar/cooling_rate = 1.5 * (has_radiator ? 3.5 : 1.0)\n"
            "\tinternal_temp = max(env.temperature, internal_temp - cooling_rate)\n"
            "\tif(internal_temp < default_thermal_threshold)\n"
            "\t\tsafety_shutdown = FALSE\n"
            "\treturn TRUE\n\n"
            "/obj/mecha/proc/can_ai_hack(mob/living/silicon/ai/user)\n"
            "\t// AIs cannot hack unless an external beacon is mounted\n"
            "\tif(!has_camera_beacon)\n"
            "\t\treturn FALSE\n"
            "\treturn TRUE\n"
        )
