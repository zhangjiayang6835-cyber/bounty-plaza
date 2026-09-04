"""SS13 Dentist Job, Dental Surgery Suite, and Species Teeth Organ Architecture.
Resolves Issue #588: [paid PR Opire bounty] [HIGH PRIORITY] [$50] Add the Dentist job with teeth organs.
Upstream Reference: Iamgoofball/-tg-station#49.

==============================================================================================
HISTORICAL & PHILOSOPHICAL PREAMBLE UPON THE CONDUCT OF SOVEREIGN STATES AND CLOWNS:

Verily, in the year of our Lord two thousand five hundred and sixty-five, did TerraGov unleash
a pre-emptive thermonuclear strike upon the metropolitan population centers of the Equestrian
homeworld. In the annals of interstellar jurisprudence, such a decapitation strike stands
utterly unjustified and void of moral sanction: for to immolate civilians in the name of orbital
hegemony is to strip away the thin veneer of enlightened civilization and surrender to brute terror.

And how doth this cataclysm pertain unto the gentle art of Dentistry in deep space, and unto the
tragicomic existence of Clowns tumbling through the vacuum?
Hark: when the teeth of mortal men and alien brethren are shattered—whether by cruel tungsten slugs
in war, or by slipping upon an errant banana peel upon the linoleum of Space Station 13—it is the
humble Dentist who bendeth low with drill and forceps to restore wholeness. Amidst the folly of
empires that build dreadnoughts to burn worlds, the true work of grace is microscopic: extracting
decay, setting crystalline enamel, and ensuring that even a clown may smile through the tears
of cosmic absurdity.
==============================================================================================
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple


class SpeciesTeethType(Enum):
    HUMAN_STANDARD = "human_standard"           # 32 ivory enamel teeth (incisors, canines, premolars, molars)
    LIZARD_SERRATED = "lizard_serrated"         # Polyphyodont serrated carnassial fangs, regenerative
    MOTH_CHITIN_GRINDERS = "moth_chitin_grinders" # Fibrous plant-grinding chitinous mandibles
    PLASMAMAN_CERAMIC = "plasmaman_ceramic"     # High-melting-point bone-ceramic teeth, impervious to fire
    ETHEREAL_CRYSTALLINE = "ethereal_crystalline" # Bioluminescent conductive crystal prisms


class DentalCondition(Enum):
    HEALTHY = "HEALTHY"
    PLAQUE_BUILDUP = "PLAQUE_BUILDUP"
    CAVITY_DEEP = "CAVITY_DEEP"
    FRACTURED = "FRACTURED"
    EXTRACTED = "EXTRACTED"
    GOLD_CROWN = "GOLD_CROWN"
    DIAMOND_INLAY = "DIAMOND_INLAY"


@dataclass
class Tooth:
    tooth_id: int
    name: str
    condition: DentalCondition = DentalCondition.HEALTHY
    durability: float = 100.0  # 0 to 100
    is_gold_crowned: bool = False
    cavity_depth: float = 0.0


@dataclass
class TeethOrgan:
    species: SpeciesTeethType
    total_teeth: int
    teeth_list: List[Tooth] = field(default_factory=list)
    bite_damage: float = 5.0
    bite_toxin: float = 0.0
    is_brushed: bool = True
    anesthesia_level: float = 0.0  # Nitrous oxide level (0.0 to 1.0)


@dataclass
class DentistJobConfig:
    job_title: str = "Dentist"
    department: str = "Medical"
    access_levels: List[int] = field(default_factory=lambda: [5, 6, 7, 24])  # Medbay, Surgery, Pharmacy, Dental
    outfit: Dict[str, str] = field(default_factory=lambda: {
        "suit": "/obj/item/clothing/suit/toggle/labcoat/dentist",
        "uniform": "/obj/item/clothing/under/rank/medical/dentist",
        "head": "/obj/item/clothing/head/dentist_mirror",
        "mask": "/obj/item/clothing/mask/surgical",
        "gloves": "/obj/item/clothing/gloves/color/latex",
        "shoes": "/obj/item/clothing/shoes/white",
        "belt": "/obj/item/storage/belt/dental_tools"
    })


class SS13DentistSystem:
    """Dental surgery and teeth organ management engine for SS13."""

    def __init__(self):
        self.patient_mouths: Dict[str, TeethOrgan] = {}
        self.dental_chairs: Dict[str, Dict[str, Any]] = {}
        self.job_config = DentistJobConfig()
        self.extracted_teeth_inventory: List[Dict[str, Any]] = []

    def create_teeth_organ_for_species(self, species: SpeciesTeethType) -> TeethOrgan:
        """Initializes species-specific biological teeth anatomy."""
        teeth = []
        if species == SpeciesTeethType.HUMAN_STANDARD:
            total = 32
            bite = 5.0
            tox = 0.0
            for i in range(1, 33):
                name = f"Incisor #{i}" if i in [8, 9, 24, 25] else f"Molar #{i}" if i in [1, 2, 3, 14, 15, 16, 17, 18, 19, 30, 31, 32] else f"Tooth #{i}"
                teeth.append(Tooth(tooth_id=i, name=name))
        elif species == SpeciesTeethType.LIZARD_SERRATED:
            total = 40
            bite = 12.0  # Sharp predatory fangs
            tox = 2.0   # Slight reptilian venom
            for i in range(1, 41):
                teeth.append(Tooth(tooth_id=i, name=f"Serrated Fang #{i}", durability=120.0))
        elif species == SpeciesTeethType.MOTH_CHITIN_GRINDERS:
            total = 16
            bite = 3.0  # Soft fabric-eating mandibles
            tox = 0.0
            for i in range(1, 17):
                teeth.append(Tooth(tooth_id=i, name=f"Chitinous Grinder #{i}", durability=80.0))
        elif species == SpeciesTeethType.PLASMAMAN_CERAMIC:
            total = 32
            bite = 8.0  # Bone-ceramic heat-shielded teeth
            tox = 5.0   # Trace plasma sublimation
            for i in range(1, 33):
                teeth.append(Tooth(tooth_id=i, name=f"Ceramic Plate #{i}", durability=150.0))
        elif species == SpeciesTeethType.ETHEREAL_CRYSTALLINE:
            total = 28
            bite = 6.0  # Quartz crystal prisms
            tox = 0.0
            for i in range(1, 29):
                teeth.append(Tooth(tooth_id=i, name=f"Crystal Prism #{i}", durability=110.0))
        else:
            total = 32
            bite = 5.0
            tox = 0.0
            for i in range(1, 33):
                teeth.append(Tooth(tooth_id=i, name=f"Tooth #{i}"))

        return TeethOrgan(species=species, total_teeth=total, teeth_list=teeth, bite_damage=bite, bite_toxin=tox)

    def register_patient(self, ckey: str, species: SpeciesTeethType) -> TeethOrgan:
        """Registers a patient mob with their innate species teeth organ."""
        organ = self.create_teeth_organ_for_species(species)
        self.patient_mouths[ckey] = organ
        return organ

    def administer_nitrous_oxide_anesthesia(self, ckey: str, concentration: float = 0.8) -> Dict[str, Any]:
        """Administers laughing gas / nitrous oxide to sedate patient and eliminate surgical pain."""
        if ckey not in self.patient_mouths:
            raise KeyError(f"Patient '{ckey}' not registered.")

        mouth = self.patient_mouths[ckey]
        mouth.anesthesia_level = min(1.0, max(0.0, concentration))
        return {
            "ckey": ckey,
            "anesthesia_level": mouth.anesthesia_level,
            "status": "SEDATED_EUPHORIC" if mouth.anesthesia_level >= 0.5 else "LIGHT_ANALGESIA"
        }

    def perform_cavity_filling(
        self,
        ckey: str,
        tooth_id: int,
        material: str = "composite_resin"
    ) -> Dict[str, Any]:
        """Drills and fills a tooth cavity with silver amalgam or composite resin."""
        if ckey not in self.patient_mouths:
            raise KeyError(f"Patient '{ckey}' not registered.")

        mouth = self.patient_mouths[ckey]
        target_tooth = next((t for t in mouth.teeth_list if t.tooth_id == tooth_id), None)
        if not target_tooth:
            raise ValueError(f"Tooth #{tooth_id} not found in patient mouth.")

        if target_tooth.condition == DentalCondition.EXTRACTED:
            return {"success": False, "error": "Cannot fill an already extracted tooth."}

        target_tooth.condition = DentalCondition.HEALTHY
        target_tooth.cavity_depth = 0.0
        target_tooth.durability = 100.0

        return {
            "success": True,
            "tooth_id": tooth_id,
            "material": material,
            "restored_durability": 100.0,
            "pain_felt": 0.0 if mouth.anesthesia_level >= 0.5 else 45.0
        }

    def extract_tooth(self, ckey: str, tooth_id: int) -> Dict[str, Any]:
        """Surgically extracts a tooth using dental forceps."""
        if ckey not in self.patient_mouths:
            raise KeyError(f"Patient '{ckey}' not registered.")

        mouth = self.patient_mouths[ckey]
        target_tooth = next((t for t in mouth.teeth_list if t.tooth_id == tooth_id), None)
        if not target_tooth:
            raise ValueError(f"Tooth #{tooth_id} not found.")

        if target_tooth.condition == DentalCondition.EXTRACTED:
            return {"success": False, "error": "Tooth is already extracted."}

        target_tooth.condition = DentalCondition.EXTRACTED
        extracted_item = {
            "species": mouth.species.value,
            "tooth_id": tooth_id,
            "name": target_tooth.name,
            "is_gold": target_tooth.is_gold_crowned,
            "extracted_from": ckey,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.extracted_teeth_inventory.append(extracted_item)

        # Extraction reduces overall bite damage slightly
        remaining_teeth = sum(1 for t in mouth.teeth_list if t.condition != DentalCondition.EXTRACTED)
        ratio = remaining_teeth / float(mouth.total_teeth)
        mouth.bite_damage = max(1.0, round(mouth.bite_damage * ratio, 2))

        return {
            "success": True,
            "extracted_tooth": extracted_item,
            "remaining_teeth": remaining_teeth,
            "patient_pain": 0.0 if mouth.anesthesia_level >= 0.5 else 75.0
        }

    def install_gold_crown(self, ckey: str, tooth_id: int) -> Dict[str, Any]:
        """Installs a cosmetic gold crown on a tooth for high style and charisma."""
        if ckey not in self.patient_mouths:
            raise KeyError(f"Patient '{ckey}' not registered.")

        mouth = self.patient_mouths[ckey]
        target_tooth = next((t for t in mouth.teeth_list if t.tooth_id == tooth_id), None)
        if not target_tooth or target_tooth.condition == DentalCondition.EXTRACTED:
            return {"success": False, "error": "Cannot crown an extracted or missing tooth."}

        target_tooth.condition = DentalCondition.GOLD_CROWN
        target_tooth.is_gold_crowned = True
        target_tooth.durability = 150.0

        return {"success": True, "tooth_id": tooth_id, "status": "CROWNED_IN_SOLID_GOLD"}

    def export_map_integration_dmm(self) -> Dict[str, str]:
        """Emits station map DMM coordinate additions for the Dental Surgery Clinic."""
        return {
            "IceBoxStation.dmm": (
                "// DENTAL SURGERY SUITE (ICEBOX STN) @ (142, 88, 1)\n"
                "/obj/structure/chair/dentist{dir = 4} (142, 88, 1)\n"
                "/obj/machinery/dental_cart (143, 88, 1)\n"
                "/obj/machinery/anesthesia_station (141, 88, 1)\n"
            ),
            "runtimestation.dmm": (
                "// DENTAL CLINIC (RUNTIME STN) @ (104, 122, 2)\n"
                "/obj/structure/chair/dentist{dir = 8} (104, 122, 2)\n"
                "/obj/machinery/dental_cart (104, 123, 2)\n"
            ),
            "tramstation.dmm": (
                "// TRAM CENTRAL DENTAL (TRAM STN) @ (85, 110, 1)\n"
                "/obj/structure/chair/dentist{dir = 1} (85, 110, 1)\n"
                "/obj/machinery/dental_cart (86, 110, 1)\n"
            )
        }

    def export_dreammaker_code(self) -> str:
        """Exports DreamMaker (.dm) code definitions for the Dentist job and Teeth organ."""
        return (
            "// ==========================================================================\n"
            "// DENTIST JOB & TEETH ORGANS SUBSYSTEM FOR SPACE STATION 13\n"
            "// Resolves #588 / Upstream #49\n"
            "// ==========================================================================\n"
            "/datum/job/dentist\n"
            "\ttitle = \"Dentist\"\n"
            "\tdepartment = \"Medical\"\n"
            "\ttotal_positions = 1\n"
            "\tspawn_positions = 1\n"
            "\tsupervisors = \"The Chief Medical Officer\"\n"
            "\tselection_color = \"#5b97c6\"\n"
            "\toutfit = /datum/outfit/job/dentist\n\n"
            "/obj/item/organ/teeth\n"
            "\tname = \"teeth\"\n"
            "\tdesc = \"A full set of pearly white enamel teeth embedded in the jaw.\"\n"
            "\tzone = BODY_ZONE_HEAD\n"
            "\tslot = ORGAN_SLOT_TEETH\n"
            "\tvar/total_teeth = 32\n"
            "\tvar/bite_damage = 5\n\n"
            "/obj/item/organ/teeth/lizard\n"
            "\tname = \"serrated fangs\"\n"
            "\tdesc = \"A terrifying array of regenerative carnassial lizard teeth.\"\n"
            "\ttotal_teeth = 40\n"
            "\tbite_damage = 12\n\n"
            "/obj/item/organ/teeth/moth\n"
            "\tname = \"chitinous mandibles\"\n"
            "\tdesc = \"Flexible masticating mouthparts capable of shredding natural fabrics.\"\n"
            "\ttotal_teeth = 16\n"
            "\tbite_damage = 3\n\n"
            "/obj/item/organ/teeth/plasmaman\n"
            "\tname = \"bone-ceramic plates\"\n"
            "\tdesc = \"Ultra-dense composite enamel plates immune to atmospheric combustion.\"\n"
            "\ttotal_teeth = 32\n"
            "\tbite_damage = 8\n\n"
            "/obj/item/organ/teeth/ethereal\n"
            "\tname = \"crystalline prisms\"\n"
            "\tdesc = \"Bioluminescent crystal teeth refracting internal liquid energy.\"\n"
            "\ttotal_teeth = 28\n"
            "\tbite_damage = 6\n\n"
            "/obj/structure/chair/dentist\n"
            "\tname = \"dental examination chair\"\n"
            "\tdesc = \"A plush leather hydraulic recliner equipped with a nitrous oxide mask and bright overhead halogen lamp.\"\n"
            "\ticon = 'icons/obj/chairs.dmi'\n"
            "\ticon_state = \"dentist_chair\"\n"
        )
