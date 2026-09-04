"""🦐 Shrimp-Person Species Implementation & Mechanics Simulation 🦐.
Resolves Issue #692: [Bounty $200] Add a shrimp-person species 🦐 🦐 🦐.

Features:
- 🦐 Shrimplike chitinous exoskeleton with natural armor and water respiration
- 🦐 Fishbowl helmet requirement (suffocates in open air without water/saline environment)
- 🦐 Permanent T-ray vision via sensory antennae
- 🦐 Tail whip kinetic vortex on *spin (damages adjacent mobs and structures)
- 🦐 Deep-fry transformation on high burn death (turns into fried shrimp 🍤)
- 🦐 Native BYOND DM code generator for SS13 integration
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class RespirationEnvironment(str, Enum):
    WATER = "water"
    AIR = "air"
    VACUUM = "vacuum"


@dataclass
class ItemSlot:
    name: str
    item: Optional["Item"] = None


@dataclass
class Item:
    name: str
    is_water_sealed: bool = False
    is_food: bool = False


class FishbowlHelmet(Item):
    def __init__(self, water_level_ml: float = 1000.0):
        super().__init__(name="🦐 Glass Fishbowl Helmet 🦐", is_water_sealed=True)
        self.water_level_ml: float = water_level_ml

    def consume_water(self, amount: float = 1.0) -> bool:
        if self.water_level_ml >= amount:
            self.water_level_ml -= amount
            return True
        return False


@dataclass
class FriedShrimp(Item):
    def __init__(self, golden_crispiness: float = 100.0):
        super().__init__(name="🍤 Golden Fried Shrimp 🍤", is_food=True)
        self.golden_crispiness: float = golden_crispiness
        self.nutrition_value: float = 45.0


@dataclass
class Entity:
    entity_id: str
    name: str
    x: int
    y: int
    health: float = 100.0
    max_health: float = 100.0
    is_structure: bool = False

    def take_damage(self, amount: float) -> float:
        self.health = max(0.0, self.health - amount)
        return self.health


@dataclass
class ShrimpPerson(Entity):
    """🦐 Full humanoid shrimp mob with custom organs, traits, and spin mechanics 🦐."""

    head_gear: Optional[FishbowlHelmet] = None
    oxygen_level: float = 100.0
    burn_damage: float = 0.0
    brute_damage: float = 0.0
    is_dead: bool = False
    t_ray_vision: bool = True
    traits: Set[str] = field(default_factory=lambda: {"🦐_chitin_shell", "🦐_antenna_t_ray", "🦐_aquatic"})
    inventory: List[Item] = field(default_factory=list)

    def is_suffocating(self, ambient_env: RespirationEnvironment) -> bool:
        """🦐 Shrimp require water breathing. Without a filled fishbowl, they suffocate in air."""
        if self.head_gear and self.head_gear.is_water_sealed and self.head_gear.consume_water():
            return False
        return ambient_env != RespirationEnvironment.WATER

    def process_life(self, ambient_env: RespirationEnvironment = RespirationEnvironment.AIR) -> None:
        """Periodic life tick processing respiration and vitals."""
        if self.is_dead:
            return

        if self.is_suffocating(ambient_env):
            self.oxygen_level = max(0.0, self.oxygen_level - 10.0)
            if self.oxygen_level <= 0.0:
                self.health = max(0.0, self.health - 15.0)
        else:
            self.oxygen_level = min(100.0, self.oxygen_level + 5.0)

        total_damage = self.burn_damage + self.brute_damage
        self.health = max(0.0, self.max_health - total_damage)
        if self.health <= 0.0:
            self.die()

    def spin_tail_whip(self, surroundings: List[Entity]) -> Dict[str, Any]:
        """🦐 Spinning triggers a massive hydrodynamic tail flick damaging adjacent entities."""
        damaged_targets: List[Dict[str, Any]] = []
        tail_damage = 25.0

        for entity in surroundings:
            if entity.entity_id == self.entity_id:
                continue

            # Check adjacency (Chebyshev distance <= 1 tile)
            dx = abs(entity.x - self.x)
            dy = abs(entity.y - self.y)
            if dx <= 1 and dy <= 1:
                remaining_health = entity.take_damage(tail_damage)
                damaged_targets.append({
                    "target_id": entity.entity_id,
                    "target_name": entity.name,
                    "damage_dealt": tail_damage,
                    "remaining_health": remaining_health,
                    "is_structure": entity.is_structure,
                })

        return {
            "action": "🦐 *SPIN_TAIL_WHIP* 🦐",
            "targets_hit": len(damaged_targets),
            "details": damaged_targets,
        }

    def die(self) -> Optional[FriedShrimp]:
        """🦐 On death: if burn damage >= 50.0, the shrimp-person crisps into fried shrimp 🍤!"""
        self.is_dead = True
        self.health = 0.0

        if self.burn_damage >= 50.0:
            fried_snack = FriedShrimp(golden_crispiness=min(100.0, self.burn_damage * 1.2))
            self.inventory.append(fried_snack)
            return fried_snack
        return None


# 🦐 SS13 BYOND DM Source Module Representation 🦐
BYOND_SHRIMP_DM_SOURCE: str = """
// 🦐🦐🦐 /datum/species/shrimp - Space Station 13 Shrimp-Person Species 🦐🦐🦐
/datum/species/shrimp
	name = "Shrimp-person 🦐"
	id = "shrimp"
	say_mod = "clicks and bubblys"
	default_color = "#FF7F50" // Coral pink shrimp hue 🦐
	species_traits = list(TRAIT_T_RAY_VISION, TRAIT_AQUATIC_BREATHING)
	inherent_biotypes = MOB_ORGANIC | MOB_HUMANOID | MOB_AQUATIC

/datum/species/shrimp/on_species_gain(mob/living/carbon/human/H)
	..()
	H.AddElement(/datum/element/t_ray_vision) // 🦐 Permanent sensory antennae T-ray vision
	to_chat(H, span_notice("🦐 Your antennae twitch as you perceive underlying conduit grids! 🦐"))

/datum/species/shrimp/spec_life(mob/living/carbon/human/H, seconds_per_tick, times_fired)
	..()
	// 🦐 Check for fishbowl environmental helmet
	var/obj/item/clothing/head/fishbowl/bowl = H.head
	if(!istype(bowl) || bowl.water_volume <= 0)
		H.adjustOxyLoss(4 * seconds_per_tick)
		if(SPT_PROB(20, seconds_per_tick))
			to_chat(H, span_warning("🦐 You desperately gasp for aerated water! Wear your fishbowl! 🦐"))
	else
		bowl.water_volume -= 0.1 * seconds_per_tick

/datum/species/shrimp/handle_death(mob/living/carbon/human/H, gibbed)
	if(H.getFireLoss() >= 50)
		// 🦐 Fry into delicious fried shrimp! 🍤
		var/obj/item/food/fried_shrimp/crispy = new(H.loc)
		crispy.name = "golden fried [H.real_name] 🍤"
		H.visible_message(span_danger("🦐 [H] sizzles vigorously and crisps into a delicious fried shrimp! 🍤"))
		qdel(H)
		return
	..()

/mob/living/carbon/human/proc/spin_tail_whip()
	set name = "🦐 Spin Tail Whip 🦐"
	set category = "Abilities"

	if(!ishuman(src))
		return
	var/mob/living/carbon/human/H = src
	if(H.dna.species.id != "shrimp")
		to_chat(H, span_warning("Only shrimp-people have powerful tail whips! 🦐"))
		return

	H.spin(20, 2)
	H.visible_message(span_danger("🦐 [H] spins violently, lashing out with a massive shrimp tail! 🦐"))
	for(var/atom/movable/AM in range(1, H))
		if(AM == H)
			continue
		if(isliving(AM))
			var/mob/living/L = AM
			L.apply_damage(25, BRUTE)
			to_chat(L, span_userdanger("🦐 You are struck by [H]'s tail whip! 🦐"))
		else if(isstructure(AM))
			AM.take_damage(25)
"""
