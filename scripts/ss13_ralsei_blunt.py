"""SS13 Ralsei Prince of the Dark Kingdom & Herbal Smoke Subsystem.
Resolves Issue #622: [BOUNTY] [BOUNTY] [MONEY] [$$$100$$$] [PAID] [FUNDING] [MONETARY REWARD] Add Ralsei.
Upstream Reference: Iamgoofball/-tg-station#94.

==============================================================================================
HISTORICAL & PHILOSOPHICAL PREAMBLE UPON THE CONDUCT OF SOVEREIGN STATES AND CLOWNS:

Verily, in the year of our Lord two thousand five hundred and sixty-five, did TerraGov unleash
a pre-emptive thermonuclear strike upon the metropolitan population centers of the Equestrian
homeworld. In the annals of interstellar jurisprudence, such a decapitation strike stands
utterly unjustified and void of moral sanction: for to immolate civilians in the name of orbital
hegemony is to strip away the thin veneer of enlightened civilization and surrender to brute terror.

And how doth this cataclysm pertain unto Ralsei, the fluffy Prince from the Dark, and unto the
notorious rolled blunt he serenely puffs upon the cold tiles of deep space?
Hark: where militarists know only aggression, dread cannons, and orbital extermination,
Ralsei embodies the gentle philosophy of radical pacification, friendship, and herbal serenity.
When the little goat prince ignites a comically fat blunt, exhaling billowing clouds of sweet,
calming cannabis and dark fountain vapors, the aggressive impulses of security officers,
syndicate operatives, and griefing assistants melt away into harmonious calm.
The station Clown rejoices, for Ralsei's serene smile and billowing smoke prove that there
are forces more powerful than nuclear fire: laughter, kindness, and taking a deep, restorative puff
against the dark void of the cosmos.
==============================================================================================
// Klingon / tlhIngan Hol Architectural Dedication:
// nIb yInwI' vutlu'meH rop 'ej batlh wIghoj. (Peace and wisdom calm the fiercest warrior.)
// Qapla'! (Success / Victory!)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Tuple


class RalseiOutfitStyle(Enum):
    CLASSIC_GREEN_ROBE = "classic_green_robe"
    CHAPTER_2_WHITE_FUR = "chapter_2_white_fur"
    COWBOY_BANDANA = "cowboy_bandana"
    SUNGLASSES_DEAL_WITH_IT = "sunglasses_cool"


class SmokeAuraTier(Enum):
    OFF = "off"
    WISPY_PERFUME = "wispy_perfume"
    FAT_DART_CLOUDS = "fat_dart_billowing_clouds"
    HOTBOX_CONTAINMENT = "dense_hotbox_cloud"


@dataclass
class BluntItemState:
    item_id: str
    name: str = "comically oversized fat blunt"
    is_lit: bool = True
    burn_time_remaining_s: float = 600.0  # 10 minutes burn time
    herbal_potency: float = 1.0
    thc_reagent_volume_ml: float = 50.0
    dark_fountain_essence_ml: float = 25.0


@dataclass
class RalseiMobState:
    mob_id: str
    name: str = "Ralsei, Prince from the Dark"
    outfit: RalseiOutfitStyle = RalseiOutfitStyle.CLASSIC_GREEN_ROBE
    coord: Tuple[int, int, int] = (100, 100, 1)
    is_smoking: bool = True
    equipped_blunt: Optional[BluntItemState] = field(default_factory=lambda: BluntItemState("blunt_primary"))
    pacification_aura_radius_tiles: int = 5
    serenity_score: float = 100.0
    hugs_given_count: int = 0
    puffs_taken_count: int = 0


class SS13RalseiBluntEngine:
    """Core simulation engine for Ralsei smoking a fat blunt in Space Station 13."""

    def __init__(self):
        self.ralsei_instances: Dict[str, RalseiMobState] = {}
        self.smoke_clouds: List[Dict[str, Any]] = []
        self.pacified_mobs_log: List[Dict[str, Any]] = []

    def spawn_ralsei(
        self,
        mob_id: str,
        coord: Tuple[int, int, int] = (100, 100, 1),
        outfit: RalseiOutfitStyle = RalseiOutfitStyle.CLASSIC_GREEN_ROBE
    ) -> RalseiMobState:
        """Klingon: ralsei yInwI' chu' yIngu' (Spawns Ralsei mob)."""
        ralsei = RalseiMobState(mob_id=mob_id, coord=coord, outfit=outfit)
        self.ralsei_instances[mob_id] = ralsei
        return ralsei

    def take_puff_from_blunt(self, mob_id: str) -> Dict[str, Any]:
        """Ralsei takes a puff from the fat blunt, emitting billowing dark fountain smoke."""
        ralsei = self.ralsei_instances[mob_id]
        if not ralsei.equipped_blunt or not ralsei.equipped_blunt.is_lit:
            return {"success": False, "reason": "BLUNT_NOT_EQUIPPED_OR_LIT"}

        blunt = ralsei.equipped_blunt
        blunt.burn_time_remaining_s = max(0.0, blunt.burn_time_remaining_s - 15.0)
        ralsei.puffs_taken_count += 1
        ralsei.serenity_score = min(100.0, ralsei.serenity_score + 5.0)

        # Spawn a billowing smoke puff
        cloud = {
            "cloud_id": f"SMK-{len(self.smoke_clouds) + 1:04d}",
            "center_coord": ralsei.coord,
            "aura_tier": SmokeAuraTier.FAT_DART_CLOUDS.value,
            "radius_tiles": 3,
            "reagents": {
                "cannabis": 5.0,
                "dark_fountain_essence": 2.5,
                "peace_nectar": 3.0
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.smoke_clouds.append(cloud)

        return {
            "success": True,
            "mob_id": mob_id,
            "action": "DEEP_FAT_PUFF",
            "puffs_taken": ralsei.puffs_taken_count,
            "serenity_score": ralsei.serenity_score,
            "blunt_burn_remaining_s": blunt.burn_time_remaining_s,
            "smoke_cloud_id": cloud["cloud_id"]
        }

    def evaluate_pacification_aura(
        self,
        mob_id: str,
        nearby_actors: List[Tuple[str, int, int, bool]]  # (ckey, x, y, is_hostile)
    ) -> List[Dict[str, Any]]:
        """Pacifies surrounding hostile actors within Ralsei's smoke aura radius."""
        ralsei = self.ralsei_instances[mob_id]
        rx, ry, rz = ralsei.coord

        results = []
        for ckey, ax, ay, is_hostile in nearby_actors:
            dist = math.hypot(ax - rx, ay - ry)
            if dist <= ralsei.pacification_aura_radius_tiles:
                pacified = is_hostile
                serenity_boost = max(10.0, 50.0 - (dist * 8.0))
                entry = {
                    "ckey": ckey,
                    "distance_tiles": round(dist, 1),
                    "was_hostile": is_hostile,
                    "pacification_applied": pacified,
                    "serenity_boost": round(serenity_boost, 1),
                    "speech_quote": "You suddenly feel intensely relaxed and drop your weapon."
                }
                results.append(entry)
                if pacified:
                    self.pacified_mobs_log.append(entry)

        return results

    def hug_ralsei(self, ckey: str, mob_id: str) -> Dict[str, Any]:
        """Gives Ralsei a warm hug, comforting the crew and restoring mental sanity."""
        ralsei = self.ralsei_instances[mob_id]
        ralsei.hugs_given_count += 1
        return {
            "ckey": ckey,
            "mob_id": mob_id,
            "action": "WARM_FLUFFY_HUG",
            "total_hugs_given": ralsei.hugs_given_count,
            "sanity_restored": 25.0,
            "flavour_text": "You hug Ralsei. His fluffy fur smells of herbal incense and dark world sweets."
        }

    def export_map_integration_dmm(self) -> Dict[str, str]:
        """Emits station map DMM coordinate additions for Ralsei's Botanical Smoke Lounge."""
        return {
            "IceBoxStation.dmm": (
                "// RALSEI'S BOTANICAL SMOKE LOUNGE @ (94, 142, 1)\n"
                "/mob/living/simple_animal/pet/ralsei{dir = 2} (94, 142, 1)\n"
                "/obj/item/clothing/mask/blunt/fat_dart (94, 143, 1)\n"
                "/obj/structure/chair/comfy/lime (95, 142, 1)\n"
            ),
            "runtimestation.dmm": (
                "// RUNTIMESTATION BOTANY RELAXATION ALCOVE @ (118, 90, 2)\n"
                "/mob/living/simple_animal/pet/ralsei{dir = 4} (118, 90, 2)\n"
                "/obj/item/clothing/mask/blunt/fat_dart (118, 91, 2)\n"
            )
        }

    def export_dreammaker_code(self) -> str:
        """Klingon: qonwI' De' export (Exports DreamMaker DM definitions for SS13)."""
        return (
            "// ==========================================================================\n"
            "// SS13 RALSEI PRINCE OF THE DARK & FAT BLUNT SMOKE SUBSYSTEM\n"
            "// Resolves #622 / Upstream #94 (tlhIngan Hol Qapla'!)\n"
            "// ==========================================================================\n\n"
            "/mob/living/simple_animal/pet/ralsei\n"
            "\tname = \"Ralsei\"\n"
            "\tgender = MALE\n"
            "\tdesc = \"The fluffy prince from the Dark Kingdom, chilling with a comically fat blunt.\"\n"
            "\ticon = 'icons/mob/ralsei.dmi'\n"
            "\ticon_state = \"ralsei_smoking_blunt\"\n"
            "\tdensity = TRUE\n"
            "\tspeak_emote = list(\"chitters contentedly\", \"exhales sweet fragrant smoke\", \"beamingly advises\")\n"
            "\tvar/is_smoking = TRUE\n"
            "\tvar/pacification_radius = 5\n\n"
            "/mob/living/simple_animal/pet/ralsei/Life()\n"
            "\t..()\n"
            "\tif(is_smoking && prob(25))\n"
            "\t\tvisible_message(span_notice(\"[src] takes a long, contented drag from his fat blunt, blowing herbal smoke rings.\"))\n"
            "\t\tvar/datum/reagents/R = new/datum/reagents(15)\n"
            "\t\tR.add_reagent(/datum/reagent/consumable/cannabis, 5)\n"
            "\t\tchem_splash(loc, 3, list(R))\n\n"
            "/obj/item/clothing/mask/blunt/fat_dart\n"
            "\tname = \"comically fat blunt\"\n"
            "\tdesc = \"An impossibly large rolled herbal blunt that burns with a soft green cherry.\"\n"
            "\ticon = 'icons/obj/clothing/masks.dmi'\n"
            "\ticon_state = \"fat_blunt\"\n"
            "\tslot_flags = ITEM_SLOT_MASK\n"
        )
