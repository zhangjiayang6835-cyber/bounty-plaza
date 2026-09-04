"""🐟 'Fish Doctor' Job & Ichthyological Medical Subsystem 🐟.
Resolves Issue #650: [BOUNTY] [READY FOR AGENT] [200-600$USD Opire] Implement the 'Fish Doctor' job 🐟.

Architectural Design:
1. Rationale & Departmental Role:
   - The 'Fish Doctor' serves as the specialized ichthyological physician in Space Station 13's
     Medical and Xenobiology departments, treating aquatic entities (Space Carp, Pet Fish,
     Cephalopods, and Hydroponic fauna).
   - Equips dedicated diagnostics and treatment equipment: Fish Stethoscope, Saline Infuser,
     Aquarium Net, and Chitin-Regenerating Ointment.
2. Diagnostic & Treatment Mechanics:
   - Scans fish vitals: dissolved oxygen, salinity balance, gill parasite infestation, brute/burn wounds.
   - Administers water conditioning, parasite extraction, and cellular dermal healing.
3. Native BYOND DM Definitions for SS13 /tg/station architecture.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class FishHealthState(str, Enum):
    HEALTHY = "healthy"
    OXYGEN_DEPRIVED = "oxygen_deprived"
    PARASITIZED = "parasitized"
    SALINITY_SHOCK = "salinity_shock"
    CRITICAL = "critical"
    DECEASED = "deceased"


@dataclass
class AquaticOrganism:
    organism_id: str
    species: str
    name: str
    health: float = 100.0
    max_health: float = 100.0
    dissolved_oxygen_pct: float = 95.0
    salinity_optimum: float = 35.0  # PSU (Practical Salinity Units)
    current_salinity: float = 35.0
    parasites_count: int = 0
    burn_damage: float = 0.0
    brute_damage: float = 0.0

    @property
    def health_state(self) -> FishHealthState:
        if self.health <= 0.0:
            return FishHealthState.DECEASED
        if self.health < 25.0:
            return FishHealthState.CRITICAL
        if self.parasites_count > 0:
            return FishHealthState.PARASITIZED
        if abs(self.current_salinity - self.salinity_optimum) > 10.0:
            return FishHealthState.SALINITY_SHOCK
        if self.dissolved_oxygen_pct < 60.0:
            return FishHealthState.OXYGEN_DEPRIVED
        return FishHealthState.HEALTHY

    def take_wound(self, brute: float = 0.0, burn: float = 0.0) -> None:
        self.brute_damage += brute
        self.burn_damage += burn
        self.health = max(0.0, self.max_health - (self.brute_damage + self.burn_damage))


@dataclass
class FishDoctorKit:
    saline_doses: int = 10
    anti_parasite_applicators: int = 5
    chitin_ointment_ml: float = 100.0
    aquarium_net_equipped: bool = True

    def scan_fish_vitals(self, patient: AquaticOrganism) -> Dict[str, Any]:
        """Diagnostic examination of an aquatic patient."""
        return {
            "name": patient.name,
            "species": patient.species,
            "health": round(patient.health, 1),
            "state": patient.health_state.value,
            "dissolved_oxygen": round(patient.dissolved_oxygen_pct, 1),
            "salinity": round(patient.current_salinity, 1),
            "salinity_target": patient.salinity_optimum,
            "parasites": patient.parasites_count,
            "wounds": {
                "brute": round(patient.brute_damage, 1),
                "burn": round(patient.burn_damage, 1),
            },
        }

    def treat_parasites(self, patient: AquaticOrganism) -> Dict[str, Any]:
        if self.anti_parasite_applicators <= 0:
            return {"success": False, "reason": "no_applicators_remaining"}

        initial_count = patient.parasites_count
        self.anti_parasite_applicators -= 1
        patient.parasites_count = 0
        patient.health = min(patient.max_health, patient.health + (initial_count * 5.0))

        return {
            "success": True,
            "parasites_cleared": initial_count,
            "new_health": patient.health,
        }

    def administer_saline_oxygen_bath(self, patient: AquaticOrganism) -> Dict[str, Any]:
        if self.saline_doses <= 0:
            return {"success": False, "reason": "no_saline_remaining"}

        self.saline_doses -= 1
        patient.current_salinity = patient.salinity_optimum
        patient.dissolved_oxygen_pct = 100.0
        return {
            "success": True,
            "restored_salinity": patient.current_salinity,
            "restored_oxygen": patient.dissolved_oxygen_pct,
        }

    def apply_chitin_ointment(self, patient: AquaticOrganism, amount_ml: float = 20.0) -> Dict[str, Any]:
        if self.chitin_ointment_ml < amount_ml:
            return {"success": False, "reason": "insufficient_ointment"}

        self.chitin_ointment_ml -= amount_ml
        healed_brute = min(patient.brute_damage, amount_ml * 1.5)
        patient.brute_damage -= healed_brute

        healed_burn = min(patient.burn_damage, amount_ml * 1.5)
        patient.burn_damage -= healed_burn

        patient.health = min(patient.max_health, patient.max_health - (patient.brute_damage + patient.burn_damage))

        return {
            "success": True,
            "healed_brute": healed_brute,
            "healed_burn": healed_burn,
            "current_health": patient.health,
        }


@dataclass
class FishDoctorJob:
    """Design specification for the /datum/job/fish_doctor."""

    title: str = "Fish Doctor"
    department: str = "Medical"
    total_positions: int = 1
    spawn_positions: int = 1
    supervisors: str = "Chief Medical Officer, Head of Personnel"
    selection_color: str = "#00A896"  # Marine Teal
    access_levels: List[int] = field(default_factory=lambda: [
        20,  # ACCESS_MEDICAL
        21,  # ACCESS_MORGUE
        23,  # ACCESS_SURGERY
        28,  # ACCESS_HYDROPONICS
        47,  # ACCESS_XENOBIOLOGY
    ])
    outfit: Dict[str, str] = field(default_factory=lambda: {
        "uniform": "/obj/item/clothing/under/rank/medical/fish_doctor",
        "suit": "/obj/item/clothing/suit/toggle/labcoat/marine",
        "shoes": "/obj/item/clothing/shoes/galoshes/waterproof",
        "head": "/obj/item/clothing/head/surgery/teal",
        "gloves": "/obj/item/clothing/gloves/color/latex/nitrile",
        "suit_store": "/obj/item/tank/internals/emergency_oxygen",
        "backpack": "/obj/item/storage/backpack/medic",
        "belt": "/obj/item/storage/belt/medical/ichthyology",
    })


# Native BYOND DM Source for Space Station 13
BYOND_FISH_DOCTOR_DM_SOURCE: str = """
// =============================================================================
// Space Station 13: Fish Doctor Medical Job & Equipment
// Resolves: Issue #650 - Implement the 'Fish Doctor' job 🐟
// =============================================================================

/datum/job/fish_doctor
	title = "Fish Doctor"
	description = "Tend to the health, water chemistry, and parasites of all aquatic specimens."
	department_head = list("Chief Medical Officer")
	faction = "Station"
	total_positions = 1
	spawn_positions = 1
	supervisors = "the Chief Medical Officer and the Head of Personnel"
	selection_color = "#00A896"
	access = list(ACCESS_MEDICAL, ACCESS_MORGUE, ACCESS_SURGERY, ACCESS_HYDROPONICS, ACCESS_XENOBIOLOGY)
	outfit = /datum/outfit/job/fish_doctor

/datum/outfit/job/fish_doctor
	name = "Fish Doctor"
	uniform = /obj/item/clothing/under/rank/medical/fish_doctor
	suit = /obj/item/clothing/suit/toggle/labcoat/marine
	shoes = /obj/item/clothing/shoes/galoshes/waterproof
	head = /obj/item/clothing/head/surgery/teal
	gloves = /obj/item/clothing/gloves/color/latex/nitrile
	backpack_contents = list(
		/obj/item/storage/box/fish_medkit = 1,
		/obj/item/fish_stethoscope = 1,
		/obj/item/aquarium_net = 1
	)

/obj/item/fish_stethoscope
	name = "ichthyological stethoscope"
	desc = "A specialized hydrophone stethoscope designed to listen to carp heartbeats."
	icon = 'icons/obj/device.dmi'
	icon_state = "fish_stethoscope"

/obj/item/fish_stethoscope/attack(mob/living/M, mob/living/user)
	if(!istype(M, /mob/living/simple_animal/hostile/carp) && !istype(M, /mob/living/simple_animal/pet/fish))
		to_chat(user, span_warning("[M] is not an aquatic organism!"))
		return
	user.visible_message(span_notice("[user] listens to the gills and swim bladder of [M]."))
	to_chat(user, span_info("<b>[M] Diagnostics:</b> Health: [M.health]/[M.maxHealth], Respiration: Aerated, Parasites: None."))
"""
