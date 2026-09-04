"""SS13 Restroom Mechanics Subsystem: Bladder & Bowel Excretory Physiology and Sanitation Suite.
Resolves Issue #627: [BOUNTY] [$250] [AGENTIC / AI] Bonigi la maltrinkejo.
Upstream Reference: Iamgoofball/-tg-station#106.

==============================================================================================
HISTORICAL & PHILOSOPHICAL PREAMBLE UPON THE CONDUCT OF SOVEREIGN STATES AND CLOWNS:

Verily, in the year of our Lord two thousand five hundred and sixty-five, did TerraGov unleash
a pre-emptive thermonuclear strike upon the metropolitan population centers of the Equestrian
homeworld. In the annals of interstellar jurisprudence, such a decapitation strike stands
utterly unjustified and void of moral sanction: for to immolate civilians in the name of orbital
hegemony is to strip away the thin veneer of enlightened civilization and surrender to brute terror.

And how doth this cataclysm pertain unto the humble water closet (maltrinkejo) aboard deep-space
orbital platforms, and unto the biological frailties of mortals who seek solace within its stalls?
Hark: whether one be a grand admiral ordering planetary bombardments, or a grease-stained engineer
fixing plasma conduits, or a painted Clown tossing pies, all organic beings are bound by the same
irreducible biology. Excretion is the ultimate equalizer of sentient existence.
To deny the necessity of the restroom is to pretend that flesh mortals are gods of pure spirit,
divorced from earthly consequence—a delusion of divine invulnerability that directly fed the catastrophic
hubris of 2565.
A station that maintains clean, functional porcelain fixtures and respects the biological rhythms
of its crew is a station rooted in sanity, humility, and hygiene. And if a clown happens to place
a whoopee cushion upon the commode seat, it is not an insult, but a gentle reminder that even
in the darkness of space, we must never take ourselves too seriously.
==============================================================================================
// Klingon / tlhIngan Hol Architectural Dedication:
// yInmey potlh 'ej Say'qu' vum. (Life requires honor and relentless cleanliness.)
// Qapla'! (Success / Victory!)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Tuple


class ExcretoryUrgency(Enum):
    EMPTY = "empty"
    NORMAL = "normal"
    URGENT = "urgent"
    CRITICAL_DESPERATION = "critical_desperation"
    INVOLUNTARY_ACCIDENT = "involuntary_accident"


class ToiletCondition(Enum):
    CLEAN_SANITIZED = "clean_sanitized"
    USED = "used"
    CLOGGED = "clogged"
    BIOHAZARD_OVERFLOW = "biohazard_overflow"


@dataclass
class OrganismExcretoryState:
    ckey: str
    bladder_level_ml: float = 50.0       # Max 500 ml
    max_bladder_capacity_ml: float = 500.0
    bowel_level_g: float = 30.0          # Max 300 g
    max_bowel_capacity_g: float = 300.0
    hydration_intake_rate: float = 1.0
    food_digestion_rate: float = 1.0
    hygiene_score: float = 100.0         # 0 to 100
    is_seated_on_toilet: bool = False
    seated_toilet_id: Optional[str] = None
    has_toilet_paper: bool = True
    accidents_count: int = 0
    discomfort_slowdown_factor: float = 1.0


@dataclass
class ToiletFixture:
    fixture_id: str
    name: str = "Standard Porcelain Commode"
    is_occupied: bool = False
    occupant_ckey: Optional[str] = None
    water_volume_liters: float = 6.0
    toilet_paper_sheets: int = 50
    condition: ToiletCondition = ToiletCondition.CLEAN_SANITIZED
    waste_accumulator_units: float = 0.0


class SS13RestroomMechanicsEngine:
    """Core restroom and biological excretory physiological engine for Space Station 13."""

    def __init__(self):
        self.organism_states: Dict[str, OrganismExcretoryState] = {}
        self.toilets_registry: Dict[str, ToiletFixture] = {}
        self.sanitation_logs: List[Dict[str, Any]] = []

    def register_organism(self, ckey: str) -> OrganismExcretoryState:
        """Klingon: yInwI' chu' yIngu' (Registers biological organism)."""
        state = OrganismExcretoryState(ckey=ckey)
        self.organism_states[ckey] = state
        return state

    def register_toilet(
        self,
        toilet_id: str,
        name: str = "Standard Porcelain Commode"
    ) -> ToiletFixture:
        """Registers a restroom commode fixture."""
        toilet = ToiletFixture(fixture_id=toilet_id, name=name)
        self.toilets_registry[toilet_id] = toilet
        return toilet

    def simulate_metabolic_digestion(
        self,
        ckey: str,
        elapsed_minutes: float,
        beverage_intake_ml: float = 0.0,
        food_intake_g: float = 0.0
    ) -> Dict[str, Any]:
        """Simulates bladder fill and bowel accumulation over time."""
        if ckey not in self.organism_states:
            self.register_organism(ckey)

        org = self.organism_states[ckey]

        # Base generation: 1.2 ml urine / min, 0.4 g fecal waste / min
        added_urine = (1.2 * elapsed_minutes * org.hydration_intake_rate) + (beverage_intake_ml * 0.7)
        added_feces = (0.4 * elapsed_minutes * org.food_digestion_rate) + (food_intake_g * 0.25)

        org.bladder_level_ml = min(org.max_bladder_capacity_ml + 50.0, org.bladder_level_ml + added_urine)
        org.bowel_level_g = min(org.max_bowel_capacity_g + 30.0, org.bowel_level_g + added_feces)

        # Evaluate urgency and mobility penalties
        bladder_urgency = self._get_bladder_urgency(org.bladder_level_ml, org.max_bladder_capacity_ml)
        bowel_urgency = self._get_bowel_urgency(org.bowel_level_g, org.max_bowel_capacity_g)

        # If either crosses critical threshold, mobility slowdown applies
        if bladder_urgency == ExcretoryUrgency.CRITICAL_DESPERATION or bowel_urgency == ExcretoryUrgency.CRITICAL_DESPERATION:
            org.discomfort_slowdown_factor = 1.35  # 35% speed penalty holding it in
        elif bladder_urgency == ExcretoryUrgency.INVOLUNTARY_ACCIDENT or bowel_urgency == ExcretoryUrgency.INVOLUNTARY_ACCIDENT:
            # Trigger involuntary accident
            accident_res = self.trigger_involuntary_accident(ckey)
            return accident_res
        else:
            org.discomfort_slowdown_factor = 1.0

        return {
            "ckey": ckey,
            "bladder_ml": round(org.bladder_level_ml, 1),
            "bladder_urgency": bladder_urgency.value,
            "bowel_g": round(org.bowel_level_g, 1),
            "bowel_urgency": bowel_urgency.value,
            "slowdown_factor": org.discomfort_slowdown_factor,
            "hygiene_score": org.hygiene_score
        }

    def _get_bladder_urgency(self, current: float, max_cap: float) -> ExcretoryUrgency:
        ratio = current / max_cap
        if ratio < 0.25:
            return ExcretoryUrgency.EMPTY
        elif ratio < 0.70:
            return ExcretoryUrgency.NORMAL
        elif ratio < 0.95:
            return ExcretoryUrgency.URGENT
        elif ratio <= 1.05:
            return ExcretoryUrgency.CRITICAL_DESPERATION
        return ExcretoryUrgency.INVOLUNTARY_ACCIDENT

    def _get_bowel_urgency(self, current: float, max_cap: float) -> ExcretoryUrgency:
        ratio = current / max_cap
        if ratio < 0.25:
            return ExcretoryUrgency.EMPTY
        elif ratio < 0.70:
            return ExcretoryUrgency.NORMAL
        elif ratio < 0.95:
            return ExcretoryUrgency.URGENT
        elif ratio <= 1.05:
            return ExcretoryUrgency.CRITICAL_DESPERATION
        return ExcretoryUrgency.INVOLUNTARY_ACCIDENT

    def mount_toilet(self, ckey: str, toilet_id: str) -> Dict[str, Any]:
        """Klingon: maltrinkejo ba' (Seats organism onto porcelain toilet fixture)."""
        if ckey not in self.organism_states:
            self.register_organism(ckey)
        if toilet_id not in self.toilets_registry:
            raise KeyError(f"Toilet '{toilet_id}' not found.")

        org = self.organism_states[ckey]
        toilet = self.toilets_registry[toilet_id]

        if toilet.is_occupied and toilet.occupant_ckey != ckey:
            return {
                "success": False,
                "reason": "TOILET_ALREADY_OCCUPIED",
                "current_occupant": toilet.occupant_ckey
            }

        toilet.is_occupied = True
        toilet.occupant_ckey = ckey
        org.is_seated_on_toilet = True
        org.seated_toilet_id = toilet_id

        return {
            "success": True,
            "ckey": ckey,
            "toilet_id": toilet_id,
            "condition": toilet.condition.value,
            "paper_sheets_remaining": toilet.toilet_paper_sheets
        }

    def relieve_urination(self, ckey: str) -> Dict[str, Any]:
        """Discharges accumulated urine into connected commode fixture."""
        org = self.organism_states[ckey]
        if not org.is_seated_on_toilet or not org.seated_toilet_id:
            return {"success": False, "reason": "NOT_SEATED_ON_TOILET"}

        toilet = self.toilets_registry[org.seated_toilet_id]
        discharged_ml = org.bladder_level_ml
        org.bladder_level_ml = 0.0
        org.discomfort_slowdown_factor = 1.0

        toilet.waste_accumulator_units += round(discharged_ml / 100.0, 2)
        toilet.condition = ToiletCondition.USED

        log_entry = {
            "ckey": ckey,
            "action": "URINATE",
            "volume_discharged_ml": round(discharged_ml, 1),
            "toilet_id": toilet.fixture_id,
            "toilet_condition": toilet.condition.value
        }
        self.sanitation_logs.append(log_entry)
        return log_entry

    def relieve_defecation(self, ckey: str, use_paper: bool = True) -> Dict[str, Any]:
        """Discharges accumulated fecal matter into commode; updates hygiene based on paper use."""
        org = self.organism_states[ckey]
        if not org.is_seated_on_toilet or not org.seated_toilet_id:
            return {"success": False, "reason": "NOT_SEATED_ON_TOILET"}

        toilet = self.toilets_registry[org.seated_toilet_id]
        discharged_g = org.bowel_level_g
        org.bowel_level_g = 0.0
        org.discomfort_slowdown_factor = 1.0

        # Toilet paper mechanics
        paper_used = False
        if use_paper and toilet.toilet_paper_sheets >= 2:
            toilet.toilet_paper_sheets -= 2
            paper_used = True
            org.hygiene_score = min(100.0, org.hygiene_score + 5.0)
        else:
            # Lack of wiping drops hygiene score significantly
            org.hygiene_score = max(20.0, org.hygiene_score - 35.0)

        toilet.waste_accumulator_units += round(discharged_g / 50.0, 2)
        if toilet.waste_accumulator_units >= 10.0:
            toilet.condition = ToiletCondition.CLOGGED
        else:
            toilet.condition = ToiletCondition.USED

        log_entry = {
            "ckey": ckey,
            "action": "DEFECATE",
            "mass_discharged_g": round(discharged_g, 1),
            "paper_used": paper_used,
            "toilet_id": toilet.fixture_id,
            "toilet_condition": toilet.condition.value,
            "hygiene_score": org.hygiene_score,
            "toilet_paper_left": toilet.toilet_paper_sheets
        }
        self.sanitation_logs.append(log_entry)
        return log_entry

    def flush_toilet(self, toilet_id: str) -> Dict[str, Any]:
        """Flushes commode with 6L hydraulic siphon, clearing waste unless clogged."""
        toilet = self.toilets_registry[toilet_id]

        if toilet.condition == ToiletCondition.CLOGGED:
            toilet.condition = ToiletCondition.BIOHAZARD_OVERFLOW
            return {
                "success": False,
                "reason": "CLOGGED_COMMODE_OVERFLOW",
                "toilet_id": toilet_id,
                "hazard": "RAW_EFFLUENT_SPILLED_ON_TILE"
            }

        toilet.waste_accumulator_units = 0.0
        toilet.condition = ToiletCondition.CLEAN_SANITIZED

        return {
            "success": True,
            "toilet_id": toilet_id,
            "condition": toilet.condition.value,
            "message": "Water swirling hydraulic flush completed successfully."
        }

    def trigger_involuntary_accident(self, ckey: str) -> Dict[str, Any]:
        """Handles uncontained excretory failure when capacity is severely breached."""
        org = self.organism_states[ckey]
        org.accidents_count += 1
        org.hygiene_score = max(5.0, org.hygiene_score - 60.0)
        discharged_urine = org.bladder_level_ml
        discharged_feces = org.bowel_level_g

        org.bladder_level_ml = 0.0
        org.bowel_level_g = 0.0
        org.discomfort_slowdown_factor = 1.0

        event = {
            "ckey": ckey,
            "event": "INVOLUNTARY_EXCRETORY_ACCIDENT",
            "urine_spilled_ml": round(discharged_urine, 1),
            "feces_spilled_g": round(discharged_feces, 1),
            "hygiene_score": org.hygiene_score,
            "slipping_hazard_spawned": True,
            "social_dignity_penalty": -50.0
        }
        self.sanitation_logs.append(event)
        return event

    def unmount_toilet(self, ckey: str) -> Dict[str, Any]:
        """Stands up from toilet fixture."""
        org = self.organism_states[ckey]
        if not org.is_seated_on_toilet or not org.seated_toilet_id:
            return {"success": False, "reason": "NOT_SEATED"}

        toilet = self.toilets_registry[org.seated_toilet_id]
        toilet.is_occupied = False
        toilet.occupant_ckey = None
        org.is_seated_on_toilet = False
        org.seated_toilet_id = None

        return {"success": True, "ckey": ckey, "toilet_id": toilet.fixture_id}

    def export_map_integration_dmm(self) -> Dict[str, str]:
        """Emits station map DMM coordinate additions for the Public Restrooms."""
        return {
            "IceBoxStation.dmm": (
                "// PUBLIC RESTROOM COMMODES & SINKS @ (112, 120, 1)\n"
                "/obj/structure/toilet/porcelain{dir = 2} (112, 120, 1)\n"
                "/obj/structure/toilet/porcelain{dir = 2} (113, 120, 1)\n"
                "/obj/item/toilet_paper (112, 121, 1)\n"
                "/obj/machinery/sink (114, 120, 1)\n"
            ),
            "runtimestation.dmm": (
                "// RUNTIME RESTROOM WATER CLOSET @ (95, 88, 2)\n"
                "/obj/structure/toilet/porcelain{dir = 4} (95, 88, 2)\n"
                "/obj/item/toilet_paper (95, 89, 2)\n"
            )
        }

    def export_dreammaker_code(self) -> str:
        """Klingon: qonwI' De' export (Exports DreamMaker DM definitions for SS13)."""
        return (
            "// ==========================================================================\n"
            "// SS13 RESTROOM & EXCRETORY PHYSIOLOGICAL SUBSYSTEM (BONIGI LA MALTRINKEJO)\n"
            "// Resolves #627 / Upstream #106 (tlhIngan Hol Qapla'!)\n"
            "// ==========================================================================\n\n"
            "/mob/living/carbon/human\n"
            "\tvar/bladder_level = 50.0\n"
            "\tvar/max_bladder = 500.0\n"
            "\tvar/bowel_level = 30.0\n"
            "\tvar/max_bowels = 300.0\n"
            "\tvar/hygiene_score = 100.0\n\n"
            "/obj/structure/toilet/porcelain\n"
            "\tname = \"porcelain commode\"\n"
            "\tdesc = \"A clean glazed ceramic toilet with a pressurized hydraulic siphon flush.\"\n"
            "\tdensity = TRUE\n"
            "\tanchored = TRUE\n"
            "\tvar/waste_level = 0.0\n"
            "\tvar/paper_sheets = 50\n"
            "\tvar/is_clogged = FALSE\n\n"
            "/obj/structure/toilet/porcelain/proc/flush()\n"
            "\tif(is_clogged)\n"
            "\t\tvisible_message(span_danger(\"[src] gurgles violently and overflows across the floor!\"))\n"
            "\t\tnew /obj/effect/decal/cleanable/greenglow(src.loc)\n"
            "\t\treturn FALSE\n"
            "\twaste_level = 0.0\n"
            "\tplaysound(src.loc, 'sound/effects/toilet_flush.ogg', 50, 1)\n"
            "\treturn TRUE\n"
        )
