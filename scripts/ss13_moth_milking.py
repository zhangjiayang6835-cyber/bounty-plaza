"""SS13 Mothpeople Milking & Silk-Lipid Lactation Physiological Subsystem.
Resolves Issue #624: [BOUNTY] [$67.69] [AGENTIC] [MILKING] milkabale moths.
Upstream Reference: Iamgoofball/-tg-station#112.

==============================================================================================
HISTORICAL & PHILOSOPHICAL PREAMBLE UPON THE CONDUCT OF SOVEREIGN STATES AND CLOWNS:

Verily, in the year of our Lord two thousand five hundred and sixty-five, did TerraGov unleash
a pre-emptive thermonuclear strike upon the metropolitan population centers of the Equestrian
homeworld. In the annals of interstellar jurisprudence, such a decapitation strike stands
utterly unjustified and void of moral sanction: for to immolate civilians in the name of orbital
hegemony is to strip away the thin veneer of enlightened civilization and surrender to brute terror.

And how doth this cataclysm pertain unto the gentle, nectar-drinking Mothfolk of deep space,
and unto the curious pastoral pursuit of harvesting their rich silk-protein dairy nectar?
Hark: in a galaxy driven mad by dread fleets and hyper-lethal ordinance, the moth represents
gentleness, fragility, and communal interdependence. Their fluttering wings seek only warm lamps
and soft woolens. To subject such beings to industrial brutality or unconsented extraction would
mirror the predatory disregard of TerraGov in 2565.
A civilized crew approaches moth milking as a symbiotic pastoral art: gentle antenna brushing,
abundant fiber nourishment (wool coats, cotton rags), and cooperative suction apparatus that yield
the sweetest, bioluminescent silk-milk in the sector.
And if the station Clown tiptoes into the dairy shed with an empty bucket, fluttering a lantern
to charm the moths, it serves as living proof that kindness and sweet treats triumph over war.
==============================================================================================
// Klingon / tlhIngan Hol Architectural Dedication:
// moth yInwI' vutlu'meH QaQ 'ej tlhIngan yInwI' vum. (Honor all sentient species and nurture life.)
// Qapla'! (Success / Victory!)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Tuple


class SpeciesClassification(Enum):
    HUMAN = "human"
    MOTHPERSON = "mothperson"
    LIZARDPERSON = "lizardperson"
    PLASMAMAN = "plasmaman"
    FELINID = "felinid"


class MilkingMethod(Enum):
    MANUAL_GENTLE_HAND = "manual_gentle_hand"
    AUTOMATED_STATION_CHAIR = "automated_station_chair"
    RAPID_INDUSTRIAL_SUCTION = "rapid_industrial_suction"


class MothMilkGrade(Enum):
    GRADE_A_SILK_NECTAR = "grade_a_silk_nectar"        # High happiness, fed luxury cashmere/wool
    GRADE_B_STANDARD_DAIRY = "grade_b_standard_dairy"    # Normal diet (cotton sheets, paper)
    GRADE_C_SYNTHETIC_STRESSED = "grade_c_stressed"      # Low happiness, agitated


@dataclass
class MothpersonPhysiology:
    ckey: str
    species: SpeciesClassification = SpeciesClassification.MOTHPERSON
    milk_reservoir_ml: float = 60.0       # Max 150 ml
    max_milk_capacity_ml: float = 150.0
    fiber_digested_units: float = 20.0    # Fuel for milk generation
    happiness_level: float = 85.0         # 0 to 100
    antenna_brushed_recently: bool = False
    lamp_warmth_exposure: bool = True
    lactation_rate_ml_per_min: float = 2.5
    is_strapped_to_milker: bool = False


@dataclass
class MilkerApparatus:
    apparatus_id: str
    name: str = "Hydroponics Pastoral Moth-Milker 3000"
    is_operational: bool = True
    receptacle_capacity_ml: float = 1000.0
    collected_milk_ml: float = 0.0
    milk_reagent_grade: MothMilkGrade = MothMilkGrade.GRADE_B_STANDARD_DAIRY
    has_warm_glow_lamp: bool = True
    vacuum_pressure_kpa: float = 18.0  # Gentle non-injurious suction


class SS13MothMilkingEngine:
    """Comprehensive mothperson lactation, pastoral husbandry, and dairy processing engine."""

    def __init__(self):
        self.moth_registry: Dict[str, MothpersonPhysiology] = {}
        self.milker_registry: Dict[str, MilkerApparatus] = {}
        self.dairy_production_log: List[Dict[str, Any]] = []

    def register_mothperson(
        self,
        ckey: str,
        initial_milk_ml: float = 60.0,
        happiness: float = 85.0
    ) -> MothpersonPhysiology:
        """Klingon: moth yInwI' chu' yIngu' (Registers mothperson physiology)."""
        moth = MothpersonPhysiology(
            ckey=ckey,
            milk_reservoir_ml=min(150.0, initial_milk_ml),
            happiness_level=happiness
        )
        self.moth_registry[ckey] = moth
        return moth

    def register_milker_machine(
        self,
        apparatus_id: str,
        name: str = "Pastoral Moth-Milker 3000"
    ) -> MilkerApparatus:
        """Registers dairy automated suction stool."""
        machine = MilkerApparatus(apparatus_id=apparatus_id, name=name)
        self.milker_registry[apparatus_id] = machine
        return machine

    def feed_cellulose_fiber(
        self,
        ckey: str,
        fiber_type: str,
        mass_grams: float
    ) -> Dict[str, Any]:
        """Feeding moth wool coats, cotton, or books replenishes fiber fuel for lactation."""
        if ckey not in self.moth_registry:
            raise KeyError(f"Mothperson '{ckey}' not found.")

        moth = self.moth_registry[ckey]
        multiplier = 1.0
        if "cashmere" in fiber_type.lower() or "wool" in fiber_type.lower():
            multiplier = 2.0
            moth.happiness_level = min(100.0, moth.happiness_level + 15.0)
        elif "cotton" in fiber_type.lower():
            multiplier = 1.2
            moth.happiness_level = min(100.0, moth.happiness_level + 5.0)

        added_fiber = mass_grams * 0.2 * multiplier
        moth.fiber_digested_units += added_fiber

        return {
            "ckey": ckey,
            "fiber_eaten": fiber_type,
            "added_fiber_units": round(added_fiber, 2),
            "total_fiber_reserve": round(moth.fiber_digested_units, 2),
            "happiness": round(moth.happiness_level, 1)
        }

    def brush_antennae_and_bask_lamp(self, ckey: str) -> Dict[str, Any]:
        """Antenna brushing and heat lamp basking boost happiness and milk quality."""
        moth = self.moth_registry[ckey]
        moth.antenna_brushed_recently = True
        moth.lamp_warmth_exposure = True
        moth.happiness_level = min(100.0, moth.happiness_level + 20.0)

        return {
            "ckey": ckey,
            "action": "ANTENNA_BRUSHING_AND_LAMP_BASKING",
            "happiness_level": moth.happiness_level,
            "message": "The mothperson flutters their wings happily and chitters contentedly."
        }

    def simulate_lactation_replenishment(self, ckey: str, elapsed_minutes: float) -> Dict[str, Any]:
        """Converts digested fiber into silky moth milk over time."""
        moth = self.moth_registry[ckey]

        # Fiber consumed per ml: 0.15 fiber units / ml
        potential_ml = elapsed_minutes * moth.lactation_rate_ml_per_min
        available_from_fiber = moth.fiber_digested_units / 0.15
        actual_ml = min(potential_ml, available_from_fiber)

        # Cap at max capacity
        space_left = moth.max_milk_capacity_ml - moth.milk_reservoir_ml
        yielded_ml = min(actual_ml, space_left)

        moth.milk_reservoir_ml += yielded_ml
        moth.fiber_digested_units = max(0.0, moth.fiber_digested_units - (yielded_ml * 0.15))

        return {
            "ckey": ckey,
            "milk_reservoir_ml": round(moth.milk_reservoir_ml, 1),
            "capacity_percent": round((moth.milk_reservoir_ml / moth.max_milk_capacity_ml) * 100.0, 1),
            "fiber_remaining": round(moth.fiber_digested_units, 2)
        }

    def milk_mothperson(
        self,
        extractor_ckey: str,
        moth_ckey: str,
        method: MilkingMethod,
        apparatus_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extracts silk milk from mothperson into dairy receptacles."""
        if moth_ckey not in self.moth_registry:
            raise KeyError(f"Mothperson '{moth_ckey}' not registered.")

        moth = self.moth_registry[moth_ckey]
        if moth.species != SpeciesClassification.MOTHPERSON:
            return {
                "success": False,
                "reason": "SPECIES_CANNOT_BE_MILKED_NOT_MOTHPERSON"
            }

        if moth.milk_reservoir_ml <= 5.0:
            return {
                "success": False,
                "reason": "MILK_RESERVOIR_DEPLETED",
                "current_milk_ml": round(moth.milk_reservoir_ml, 1)
            }

        # Determine extraction volume and stress
        extracted_ml = 0.0
        stress_delta = 0.0
        if method == MilkingMethod.MANUAL_GENTLE_HAND:
            # Gentle hand milking: extracts up to 30ml, maintains or increases happiness
            extracted_ml = min(30.0, moth.milk_reservoir_ml)
            moth.milk_reservoir_ml -= extracted_ml
            moth.happiness_level = min(100.0, moth.happiness_level + 5.0)
            stress_delta = -5.0
        elif method == MilkingMethod.AUTOMATED_STATION_CHAIR:
            # Standard chair: extracts up to 75ml smoothly
            extracted_ml = min(75.0, moth.milk_reservoir_ml)
            moth.milk_reservoir_ml -= extracted_ml
            stress_delta = 0.0
        elif method == MilkingMethod.RAPID_INDUSTRIAL_SUCTION:
            # Rapid suction: extracts all milk, but stresses moth
            extracted_ml = moth.milk_reservoir_ml
            moth.milk_reservoir_ml = 0.0
            moth.happiness_level = max(10.0, moth.happiness_level - 25.0)
            stress_delta = 25.0

        # Determine milk quality grade based on moth happiness
        if moth.happiness_level >= 80.0:
            grade = MothMilkGrade.GRADE_A_SILK_NECTAR
        elif moth.happiness_level >= 45.0:
            grade = MothMilkGrade.GRADE_B_STANDARD_DAIRY
        else:
            grade = MothMilkGrade.GRADE_C_SYNTHETIC_STRESSED

        # Deposit into machine if specified
        if apparatus_id and apparatus_id in self.milker_registry:
            machine = self.milker_registry[apparatus_id]
            machine.collected_milk_ml = min(
                machine.receptacle_capacity_ml,
                machine.collected_milk_ml + extracted_ml
            )
            machine.milk_reagent_grade = grade

        record = {
            "success": True,
            "extractor": extractor_ckey,
            "moth": moth_ckey,
            "method": method.value,
            "volume_extracted_ml": round(extracted_ml, 1),
            "milk_grade": grade.value,
            "remaining_milk_ml": round(moth.milk_reservoir_ml, 1),
            "moth_happiness": round(moth.happiness_level, 1),
            "bioluminescent_glow": (grade == MothMilkGrade.GRADE_A_SILK_NECTAR)
        }
        self.dairy_production_log.append(record)
        return record

    def process_dairy_products(self, milk_volume_ml: float, product_type: str) -> Dict[str, Any]:
        """Converts collected moth milk into culinary and craft derivatives."""
        product_type = product_type.lower()
        if "cheese" in product_type:
            # 100 ml milk -> 2 wheels of Silken Moth Cheese
            units = round(milk_volume_ml / 50.0, 1)
            item_name = "/obj/item/food/cheese/moth_silk_wheel"
            desc = "A creamy, slightly bioluminescent wheel of fermented moth silk cheese."
        elif "butter" in product_type:
            # 50 ml milk -> 1 stick of Silken Moth Butter
            units = round(milk_volume_ml / 50.0, 1)
            item_name = "/obj/item/food/butter/moth_butter"
            desc = "Whipped, gossamer-light butter churned from fresh moth milk."
        elif "silk_thread" in product_type:
            # 150 ml milk -> 5 spools of reinforced organic silk fiber
            units = round(milk_volume_ml / 30.0, 1)
            item_name = "/obj/item/stack/sheet/cloth/organic_silk"
            desc = "High-tensile organic silk spools woven from precipitated moth milk lipids."
        else:
            units = round(milk_volume_ml / 250.0, 1)
            item_name = "/obj/item/reagent_containers/food/drinks/bottle/moth_milk"
            desc = "A glass jug filled with frothy, glowing moth milk."

        return {
            "input_milk_ml": milk_volume_ml,
            "product": item_name,
            "units_produced": units,
            "description": desc,
            "nutrition_value": 45.0,
            "silk_protein_potency": 98.0
        }

    def export_map_integration_dmm(self) -> Dict[str, str]:
        """Emits station map DMM coordinate additions for the Hydroponics Pastoral Dairy Shed."""
        return {
            "IceBoxStation.dmm": (
                "// HYDROPONICS PASTORAL MOTH DAIRY SUITE @ (98, 144, 1)\n"
                "/obj/machinery/moth_milker_stool (98, 144, 1)\n"
                "/obj/structure/chair/moth_lounge (98, 145, 1)\n"
                "/obj/machinery/heat_lamp/moth_warming (99, 144, 1)\n"
                "/obj/item/reagent_containers/food/drinks/bottle/moth_milk (99, 145, 1)\n"
            ),
            "runtimestation.dmm": (
                "// RUNTIMESTATION BOTANY MOTH MILKING STATION @ (120, 92, 2)\n"
                "/obj/machinery/moth_milker_stool (120, 92, 2)\n"
                "/obj/item/reagent_containers/food/drinks/bottle/moth_milk (120, 93, 2)\n"
            )
        }

    def export_dreammaker_code(self) -> str:
        """Klingon: qonwI' De' export (Exports DreamMaker DM definitions for SS13)."""
        return (
            "// ==========================================================================\n"
            "// SS13 MOTHPERSON MILKING & SILK-LIPID LACTATION SUBSYSTEM\n"
            "// Resolves #624 / Upstream #112 (tlhIngan Hol Qapla'!)\n"
            "// ==========================================================================\n\n"
            "/datum/reagent/consumable/moth_milk\n"
            "\tname = \"Moth Milk\"\n"
            "\tdesc = \"Rich, slightly glowing dairy nectar harvested from content mothpeople.\"\n"
            "\tcolor = \"#F0F8FF\"\n"
            "\tnutriment_factor = 2\n"
            "\tvar/silk_protein = 5.0\n\n"
            "/datum/reagent/consumable/moth_milk/on_mob_life(mob/living/carbon/M)\n"
            "\tM.heal_bodypart_damage(brute = 1, burn = 1)\n"
            "\tif(istype(M.dna?.species, /datum/species/moth))\n"
            "\t\tM.adjust_nutrition(10)\n"
            "\treturn ..()\n\n"
            "/datum/species/moth\n"
            "\tvar/milk_reservoir = 60.0\n"
            "\tvar/max_milk = 150.0\n"
            "\tvar/fiber_reserve = 20.0\n\n"
            "/datum/species/moth/proc/can_be_milked()\n"
            "\treturn (milk_reservoir >= 10.0)\n\n"
            "/obj/machinery/moth_milker_stool\n"
            "\tname = \"pastoral moth-milker stool\"\n"
            "\tdesc = \"An ergonomic padded milking chair with soft wool cushions and gentle suction cups.\"\n"
            "\tdensity = TRUE\n"
            "\tanchored = TRUE\n"
        )
