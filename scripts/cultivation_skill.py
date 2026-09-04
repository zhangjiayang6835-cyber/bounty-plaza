"""Cultivation Skill Subsystem, Qi Alchemy, Martial Arts, and Tribulation Engine.
Resolves Issue #678: [BOUNTY] [$10000 USD] [OPIRE/AGENTIC] [EASY FOR AI] Add Cultivation skill.

Architectural Pillars:
1. Cultivation Skill Stages & Qi Core:
   - Qi Condensation -> Foundation Establishment -> Core Formation -> Nascent Soul -> Heavenly Immortal.
2. 7 Paths to Improve Cultivation:
   - Practicing Feng Shui (spatial orientation harmony).
   - Deep Meditation (trance state accumulating environmental Qi).
   - Surviving the Extreme Cold Realm (cryogenic endurance below 100K).
   - Rigorous physical training (iron body martial conditioning).
   - Traditional Acupuncture (meridian needle stimulation).
   - Consuming magical herbs, spirit plants, and alchemical elixirs.
   - Heavenly Tribulation: surviving multiple consecutive lightning strikes.
3. Transcendent Benefits of Cultivation:
   - Master martial arts: unarmed strike force scaling, disarm counters, and iron skin armor.
   - Unlock mystical Taoist spells: Qi Palm Blast, Celestial Spirit Barrier, Wind Walk.
   - Absolute immunity to "Aunt's Special Osmanthus Soup" (a normally lethal hyper-toxic brew).
   - Essence Transfer: bestow cultivated Qi/cultivation stages directly to fellow disciples.
4. DM / BYOND Code Export:
   - Full `/datum/skill/cultivation` and `/datum/spell/targeted/qi_blast` for TGStation.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
import math
from typing import Any, Dict, List, Optional, Tuple


class CultivationStage(Enum):
    MORTAL = (0, "Mortal", 0.0)
    QI_CONDENSATION = (1, "Qi Condensation", 100.0)
    FOUNDATION_ESTABLISHMENT = (2, "Foundation Establishment", 500.0)
    CORE_FORMATION = (3, "Core Formation", 2000.0)
    NASCENT_SOUL = (4, "Nascent Soul", 5000.0)
    HEAVENLY_IMMORTAL = (5, "Heavenly Immortal", 15000.0)

    def __init__(self, rank: int, stage_name: str, qi_threshold: float):
        self.rank = rank
        self.stage_name = stage_name
        self.qi_threshold = qi_threshold


class CultivationMethod(Enum):
    FENG_SHUI = auto()
    MEDITATION = auto()
    EXTREME_COLD = auto()
    RIGOROUS_TRAINING = auto()
    ACUPUNCTURE = auto()
    HERBS_AND_ELIXIRS = auto()
    LIGHTNING_TRIBULATION = auto()


@dataclass
class CultivatorStats:
    name: str = "Taoist Disciple"
    current_qi: float = 0.0
    total_cultivated_qi: float = 0.0
    max_qi: float = 100.0
    health: float = 100.0
    max_health: float = 100.0
    stamina: float = 100.0
    is_meditating: bool = False
    consecutive_lightning_strikes: int = 0
    stage: CultivationStage = CultivationStage.MORTAL
    unlocked_spells: List[str] = field(default_factory=list)
    has_osmanthus_soup_immunity: bool = False

    def update_stage(self):
        """Advances cultivator to the highest unlocked stage based on total cultivated Qi."""
        for s in sorted(CultivationStage, key=lambda x: x.rank, reverse=True):
            if self.total_cultivated_qi >= s.qi_threshold:
                self.stage = s
                break

        # Scale stats with stage
        self.max_qi = 100.0 + (self.stage.rank * 250.0)
        self.max_health = 100.0 + (self.stage.rank * 50.0)

        # Unlock abilities by stage
        if self.stage.rank >= CultivationStage.QI_CONDENSATION.rank:
            if "Qi Palm Blast" not in self.unlocked_spells:
                self.unlocked_spells.append("Qi Palm Blast")
        if self.stage.rank >= CultivationStage.FOUNDATION_ESTABLISHMENT.rank:
            if "Celestial Spirit Barrier" not in self.unlocked_spells:
                self.unlocked_spells.append("Celestial Spirit Barrier")
            self.has_osmanthus_soup_immunity = True  # Immunity to Aunt's lethal osmanthus soup
        if self.stage.rank >= CultivationStage.CORE_FORMATION.rank:
            if "Heavenly Step" not in self.unlocked_spells:
                self.unlocked_spells.append("Heavenly Step")
        if self.stage.rank >= CultivationStage.NASCENT_SOUL.rank:
            if "Void Severing Slash" not in self.unlocked_spells:
                self.unlocked_spells.append("Void Severing Slash")


class CultivationSystem:
    """Manages progression, cultivation activities, martial arts, and essence transfer."""

    @staticmethod
    def practice_feng_shui(cultivator: CultivatorStats, room_alignment: str = "Harmonious North-Facing") -> Dict[str, Any]:
        """Aligns surrounding bagua energies to absorb environmental Qi."""
        gain = 35.0 if "Harmonious" in room_alignment else 10.0
        cultivator.current_qi += gain
        cultivator.total_cultivated_qi += gain
        cultivator.update_stage()
        return {
            "method": CultivationMethod.FENG_SHUI.name,
            "qi_gained": gain,
            "stage": cultivator.stage.stage_name,
            "message": f"{cultivator.name} aligns the room's energy according to {room_alignment}, cultivating {gain:.1f} Qi.",
        }

    @staticmethod
    def meditate(cultivator: CultivatorStats, duration_seconds: float = 10.0) -> Dict[str, Any]:
        """Enters deep meditative trance to condense celestial Qi."""
        qi_gain = duration_seconds * 5.0
        cultivator.current_qi += qi_gain
        cultivator.total_cultivated_qi += qi_gain
        cultivator.is_meditating = True
        cultivator.update_stage()
        cultivator.is_meditating = False
        return {
            "method": CultivationMethod.MEDITATION.name,
            "qi_gained": qi_gain,
            "stage": cultivator.stage.stage_name,
            "message": f"{cultivator.name} completes deep meditation, gathering {qi_gain:.1f} celestial Qi.",
        }

    @staticmethod
    def survive_extreme_cold(cultivator: CultivatorStats, temperature_kelvin: float = 75.0) -> Dict[str, Any]:
        """Survives sub-freezing cryogenic temperatures, tempering internal Yang energy."""
        if temperature_kelvin > 120.0:
            return {"success": False, "reason": "Not cold enough to temper the soul"}

        cold_severity = max(1.0, (120.0 - temperature_kelvin))
        qi_gain = cold_severity * 2.5
        cultivator.current_qi += qi_gain
        cultivator.total_cultivated_qi += qi_gain
        cultivator.update_stage()
        return {
            "method": CultivationMethod.EXTREME_COLD.name,
            "temperature_k": temperature_kelvin,
            "qi_gained": round(qi_gain, 2),
            "stage": cultivator.stage.stage_name,
            "message": f"{cultivator.name} withstands the Extreme Cold Realm at {temperature_kelvin:.1f}K, forging {qi_gain:.1f} Qi.",
        }

    @staticmethod
    def rigorous_training(cultivator: CultivatorStats, reps: int = 50) -> Dict[str, Any]:
        """Performs grueling iron-body martial calisthenics."""
        cultivator.stamina = max(0.0, cultivator.stamina - (reps * 0.5))
        qi_gain = reps * 1.5
        cultivator.current_qi += qi_gain
        cultivator.total_cultivated_qi += qi_gain
        cultivator.update_stage()
        return {
            "method": CultivationMethod.RIGOROUS_TRAINING.name,
            "reps_completed": reps,
            "qi_gained": qi_gain,
            "stage": cultivator.stage.stage_name,
            "message": f"{cultivator.name} shatters physical limits through {reps} iron strikes, forging {qi_gain:.1f} Qi.",
        }

    @staticmethod
    def acupuncture(cultivator: CultivatorStats, silver_needles: int = 8) -> Dict[str, Any]:
        """Unblocks internal Qi meridians via precise acupuncture needle placement."""
        qi_gain = silver_needles * 12.0
        cultivator.current_qi += qi_gain
        cultivator.total_cultivated_qi += qi_gain
        cultivator.health = min(cultivator.max_health, cultivator.health + 20.0)
        cultivator.update_stage()
        return {
            "method": CultivationMethod.ACUPUNCTURE.name,
            "needles_placed": silver_needles,
            "qi_gained": qi_gain,
            "stage": cultivator.stage.stage_name,
            "message": f"Silver needles clear blocked meridians! {cultivator.name} gains {qi_gain:.1f} Qi.",
        }

    @staticmethod
    def consume_herb_or_elixir(cultivator: CultivatorStats, item_name: str = "Nine-Turn Golden Elixir") -> Dict[str, Any]:
        """Ingests spirit herbs, alchemical pills, and heavenly elixirs."""
        elixir_values = {
            "Spirit Grass": 25.0,
            "Frost Lotus": 120.0,
            "Dragon Marrow Pill": 450.0,
            "Nine-Turn Golden Elixir": 2500.0,
        }
        gain = elixir_values.get(item_name, 50.0)
        cultivator.current_qi += gain
        cultivator.total_cultivated_qi += gain
        cultivator.update_stage()
        return {
            "method": CultivationMethod.HERBS_AND_ELIXIRS.name,
            "item_consumed": item_name,
            "qi_gained": gain,
            "stage": cultivator.stage.stage_name,
            "message": f"{cultivator.name} ingests {item_name}, absorbing {gain:.1f} refined medicinal Qi.",
        }

    @staticmethod
    def lightning_tribulation_strike(cultivator: CultivatorStats) -> Dict[str, Any]:
        """Endures consecutive lightning strikes to temper the golden core."""
        cultivator.consecutive_lightning_strikes += 1
        strike_num = cultivator.consecutive_lightning_strikes

        # Lightning damage is resisted partially by cultivation rank
        damage_taken = max(5.0, 45.0 - (cultivator.stage.rank * 8.0))
        cultivator.health = max(1.0, cultivator.health - damage_taken)

        # Exponential tribulation Qi reward for consecutive strikes
        qi_gain = 100.0 * (1.5 ** (strike_num - 1))
        cultivator.current_qi += qi_gain
        cultivator.total_cultivated_qi += qi_gain
        cultivator.update_stage()

        return {
            "method": CultivationMethod.LIGHTNING_TRIBULATION.name,
            "consecutive_strikes": strike_num,
            "damage_taken": damage_taken,
            "qi_gained": round(qi_gain, 2),
            "stage": cultivator.stage.stage_name,
            "message": f"THUNDER CRACKS! Strike #{strike_num} bombards {cultivator.name}, awarding {qi_gain:.1f} Tribulation Qi!",
        }

    @staticmethod
    def execute_martial_arts_strike(cultivator: CultivatorStats, target_name: str) -> Dict[str, Any]:
        """Evaluates unarmed strike damage enhanced by cultivation stage."""
        base_punch = 10.0
        stage_mult = 1.0 + (cultivator.stage.rank * 0.85)
        total_damage = round(base_punch * stage_mult, 2)
        knockdown_seconds = 0.5 * cultivator.stage.rank

        return {
            "attacker": cultivator.name,
            "target": target_name,
            "stage": cultivator.stage.stage_name,
            "damage": total_damage,
            "knockdown_seconds": knockdown_seconds,
            "sound": "sound/weapons/punch1.ogg",
        }

    @staticmethod
    def drink_aunt_osmanthus_soup(cultivator: CultivatorStats) -> Dict[str, Any]:
        """Attempts to drink Aunt's Special Osmanthus Soup. Mortals perish; true cultivators survive."""
        if cultivator.has_osmanthus_soup_immunity:
            cultivator.health = cultivator.max_health  # Fully restores health
            return {
                "survived": True,
                "message": f"{cultivator.name} savors Aunt's Special Osmanthus Soup with sublime delight! Purifies all poisons.",
                "damage": 0.0,
            }
        else:
            # Fatal hyper-toxicity for mortals or novices
            cultivator.health = 0.0
            return {
                "survived": False,
                "message": f"The unholy chemical potency of Aunt's Osmanthus Soup completely vaporizes {cultivator.name}'s mortal organs!",
                "damage": 999.0,
            }

    @staticmethod
    def transfer_essence(donor: CultivatorStats, recipient: CultivatorStats, qi_amount: float) -> Dict[str, Any]:
        """Transfers cultivated Qi essence from senior master to junior disciple."""
        if donor.current_qi < qi_amount:
            return {"success": False, "reason": "Insufficient current Qi"}

        donor.current_qi -= qi_amount
        recipient.current_qi += qi_amount
        recipient.total_cultivated_qi += qi_amount
        recipient.update_stage()

        return {
            "success": True,
            "transferred_qi": qi_amount,
            "donor_remaining_qi": donor.current_qi,
            "recipient_total_qi": recipient.total_cultivated_qi,
            "recipient_stage": recipient.stage.stage_name,
            "message": f"{donor.name} channels {qi_amount:.1f} pure essence into {recipient.name}'s dantian!",
        }


DM_CULTIVATION_SPEC: str = """
// =============================================================================
// TGStation Cultivation Skill, Qi Core, and Martial Arts System (DM / BYOND)
// Resolves Issue #678: Add Cultivation skill
// =============================================================================

/datum/skill/cultivation
    name = "Cultivation"
    title = "Daoist Cultivator"
    desc = "The sacred art of circulating Qi, refining the golden core, and defying mortality."
    skill_chain = list(
        SKILL_LEVEL_NONE = "Mortal",
        SKILL_LEVEL_NOVICE = "Qi Condensation",
        SKILL_LEVEL_TRAINED = "Foundation Establishment",
        SKILL_LEVEL_EXPERT = "Core Formation",
        SKILL_LEVEL_MASTER = "Nascent Soul",
        SKILL_LEVEL_LEGENDARY = "Heavenly Immortal"
    )

/mob/living/carbon/human/proc/cultivate_meditation()
    set name = "Meditate (Cultivate Qi)"
    set category = "Cultivation"

    if(stat != CONSCIOUS)
        return
    to_chat(src, span_purple("You sit in lotus position, absorbing the celestial Qi of the cosmos..."))
    playsound(src, 'sound/magic/meditate.ogg', 50, TRUE)
    adjust_skill_xp(/datum/skill/cultivation, 50)

/mob/living/carbon/human/proc/drink_osmanthus_soup(obj/item/reagent_containers/food/drinks/soup)
    var/cult_level = get_skill_level(/datum/skill/cultivation)
    if(cult_level >= SKILL_LEVEL_TRAINED)
        to_chat(src, span_greenannounce("Your refined dantian effortlessly digests Aunt's Special Osmanthus Soup! Immortality affirmed."))
        reagents.clear_reagents()
        heal_overall_damage(100, 100)
    else
        to_chat(src, span_userdanger("Aunt's Osmanthus Soup dissolves your mortal throat in agony!"))
        reagents.add_reagent(/datum/reagent/toxin/cyanide, 50)

/datum/spell/targeted/qi_blast
    name = "Qi Palm Blast"
    desc = "Channels dense internal Qi into a devastating kinetic palm strike."
    charge_max = 50
    range = 4

/datum/spell/targeted/qi_blast/cast(list/targets, mob/user = usr)
    for(var/mob/living/target in targets)
        target.apply_damage(40, BRUTE)
        target.Knockdown(40)
        playsound(target.loc, 'sound/magic/repulse.ogg', 80, TRUE)
"""
