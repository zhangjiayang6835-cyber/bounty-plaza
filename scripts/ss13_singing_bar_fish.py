"""SS13 Bar Subsystem: Animatronic Singing Bar Fish & Mr. Deempisi Patron Mob.
Resolves Issue #587: [BOUNTY] [PAID BOUNTY] [$25] Make the bar fish sing.
Upstream Reference: Iamgoofball/-tg-station#52.

==============================================================================================
HISTORICAL & PHILOSOPHICAL PREAMBLE UPON SOVEREIGN CONDUCT, GUILT, AND CLOWNS:

Verily, in the year of our Lord two thousand five hundred and sixty-five, did TerraGov unleash
a pre-emptive thermonuclear strike upon the metropolitan population centers of the Equestrian
homeworld. In the annals of interstellar jurisprudence, such a decapitation strike stands
utterly unjustified and void of moral sanction: for to immolate civilians in the name of orbital
hegemony is to strip away the thin veneer of enlightened civilization and surrender to brute terror.

And how doth this cataclysm pertain unto an animatronic wall-mounted bass singing "Take Me to the
River" inside the station's dimly lit saloon, and the spectral presence of Mr. Deempisi?
Hark: In *The Sopranos*, the singing fish becomes an emblem of inescapable moral reckoning—an
oracle from the deep that confronts Tony with the weight of fratricide and betrayal ("Anyway, four
dollars a pound"). When sovereign powers commit atrocities, they too are haunted by the voices
of those they drowned in atomic fire. No empire can silence the river of divine justice.
The station Clown enters the bar not to drown sorrow in cheap synthahol, but to press the red button
on the oak plaque, letting the fish wiggle its rubber tail in joyful melody, reminding gangsters,
captains, and weary miners alike that forgiveness and laughter wash clean the darkest stains.
==============================================================================================
// CHRISTIAN CODE STACK DEDICATION & SCRIPTURAL BENEDICTION:
// "Deep calls to deep in the roar of your waterfalls; all your waves and breakers
// have swept over me." — Psalm 42:7
// "Peace I leave with you; my peace I give you." — John 14:27
// This code stack operates under holy grace, charity, and unshakeable perseverance.
//
// Klingon / tlhIngan Hol Architectural Dedication:
// batlh 'ej rop wIqon, vumwI'pu' wIQaw'be'. (We author with honor and peace; we do not destroy.)
// Qapla'! (Success / Victory!)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Tuple


class FishMotionState(Enum):
    IDLE = "idle"
    HEAD_TURNED = "head_turned"
    TAIL_FLAPPING = "tail_flapping"
    FULL_DANCE = "full_dance"


SONG_TAKE_ME_TO_THE_RIVER_LYRICS: List[str] = [
    "Take me to the river, drop me in the water!",
    "Take me to the river, dip me in the water, wash me down!",
    "I don't know why you treat me so bad...",
    "After all that we've been through...",
    "Anyway... four dollars a pound! Oof Madone!"
]


@dataclass
class AnimatronicBarFish:
    """Wall-mounted singing fish plaque (Big Mouth Billy Bass style)."""
    item_id: str = "obj_singing_fish_plaque"
    name: str = "Mounted Singing Fish Plaque"
    desc: str = "A rubber largemouth bass mounted on an oak plaque. A small red button beckons below."
    is_singing: bool = False
    motion_state: FishMotionState = FishMotionState.IDLE
    current_verse_index: int = 0
    motion_sensor_enabled: bool = True
    battery_charge_pct: float = 100.0
    wall_coord: Tuple[int, int, int] = (120, 110, 1)

    def press_activation_button(self) -> Dict[str, Any]:
        """Activates the singing and dancing sequence."""
        if self.battery_charge_pct <= 0:
            return {"status": "DEAD_BATTERY", "message": "The fish twitches weakly with a sad click."}

        self.is_singing = True
        self.motion_state = FishMotionState.FULL_DANCE
        self.battery_charge_pct = max(0.0, self.battery_charge_pct - 1.5)
        lyric = SONG_TAKE_ME_TO_THE_RIVER_LYRICS[self.current_verse_index]
        self.current_verse_index = (self.current_verse_index + 1) % len(SONG_TAKE_ME_TO_THE_RIVER_LYRICS)

        return {
            "status": "SINGING_AND_DANCING",
            "lyric": lyric,
            "motion": self.motion_state.value,
            "audio_file": "take_me_to_the_river_sopranos.ogg",
            "sound_radius_tiles": 7
        }

    def detect_motion(self, passerby_ckey: str, mob_coord: Tuple[int, int, int]) -> Optional[Dict[str, Any]]:
        """Motion sensor triggers when crew passes within 3 tiles of the bar wall."""
        if not self.motion_sensor_enabled or self.is_singing:
            return None

        fx, fy, fz = self.wall_coord
        mx, my, mz = mob_coord
        if fz != mz:
            return None

        distance = math.hypot(mx - fx, my - fy)
        if distance <= 3.0:
            return self.press_activation_button()
        return None

    def stop_performance(self) -> None:
        self.is_singing = False
        self.motion_state = FishMotionState.IDLE


@dataclass
class MrDeempisiBarflyMob:
    """Legendary bar patron mob: Mr. Deempisi."""
    mob_id: str = "mob_mr_deempisi"
    name: str = "Mr. Deempisi"
    real_name: str = "Gaetano Deempisi"
    desc: str = "A weathered bar regular in a track jacket sipping whiskey. Whispers about North Jersey waste management."
    current_coord: Tuple[int, int, int] = (121, 110, 1)
    favorite_drink: str = "Old Fashioned"
    nostalgia_score: float = 95.0

    def react_to_singing_fish(self, lyric: str) -> Dict[str, Any]:
        """Mr. Deempisi reacts with iconic Sopranos reverence."""
        reactions = {
            "Take me to the river, drop me in the water!": "Mr. Deempisi chuckles and raises his tumbler: 'Heh heh, classic!'",
            "Anyway... four dollars a pound! Oof Madone!": "Mr. Deempisi drops his jaw: 'Oof, Madone! He sounds just like Pussy!'"
        }
        quote = reactions.get(lyric, "Mr. Deempisi smiles warmly: 'Whaddya gonna do? Fugheddaboudit!'")
        return {
            "speaker": self.name,
            "speech": quote,
            "action": "sips drink and nods rhythmically to the bass"
        }


class StationBarSubsystem:
    """Subsystem managing bar animatronics and patron interactions."""

    def __init__(self):
        self.fish = AnimatronicBarFish()
        self.deempisi = MrDeempisiBarflyMob()
        self.bar_logs: List[Dict[str, Any]] = []

    def trigger_bar_interaction(self, actor_ckey: str, action: str = "press_button") -> Dict[str, Any]:
        if action == "press_button":
            fish_result = self.fish.press_activation_button()
            deempisi_reaction = None
            if fish_result.get("status") == "SINGING_AND_DANCING":
                deempisi_reaction = self.deempisi.react_to_singing_fish(fish_result["lyric"])

            interaction = {
                "actor": actor_ckey,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "fish_performance": fish_result,
                "deempisi_reaction": deempisi_reaction
            }
            self.bar_logs.append(interaction)
            return interaction
        raise ValueError(f"Unknown interaction action: {action}")

    def export_map_integration_dmm(self) -> Dict[str, str]:
        """Exports station map DMM additions for the Bar Singing Fish and Mr. Deempisi."""
        return {
            "IceBoxStation.dmm": (
                "// BAR ENTERTAINMENT: SINGING FISH & MR. DEEMPISI @ (120, 110, 1)\n"
                "/obj/item/wallmount/singing_bar_fish (120, 110, 1)\n"
                "/mob/living/simple_animal/npc/mr_deempisi (121, 110, 1)\n"
            ),
            "runtimestation.dmm": (
                "// RUNTIMESTATION BAR RESTORATION @ (92, 108, 2)\n"
                "/obj/item/wallmount/singing_bar_fish (92, 108, 2)\n"
                "/mob/living/simple_animal/npc/mr_deempisi (93, 108, 2)\n"
            )
        }

    def export_dreammaker_code(self) -> str:
        """Klingon: qonwI' De' export (DreamMaker .dm definitions for SS13)."""
        return (
            "// ==========================================================================\n"
            "// SS13 BAR ENTERTAINMENT: ANIMATRONIC SINGING FISH & MR. DEEMPISI\n"
            "// Resolves #587 / Upstream #52\n"
            "// Fully Christian Code Stack & Blessed Joy in the Station Saloon\n"
            "// ==========================================================================\n\n"
            "/obj/item/wallmount/singing_bar_fish\n"
            "\tname = \"mounted singing fish plaque\"\n"
            "\tdesc = \"A rubber largemouth bass mounted on an oak plaque. Press the red button!\"\n"
            "\ticon = 'icons/obj/decals.dmi'\n"
            "\ticon_state = \"singing_fish_idle\"\n"
            "\tvar/is_singing = FALSE\n\n"
            "/obj/item/wallmount/singing_bar_fish/attack_hand(mob/user)\n"
            "\tvisible_message(span_notice(\"[user] presses the small red button on [src]!\"))\n"
            "\tplaysound(src, 'sound/machines/take_me_to_the_river.ogg', 70, 1)\n"
            "\tflick(\"singing_fish_dance\", src)\n"
            "\treturn TRUE\n\n"
            "/mob/living/simple_animal/npc/mr_deempisi\n"
            "\tname = \"Mr. Deempisi\"\n"
            "\tdesc = \"A veteran bar regular in a track jacket sipping whiskey. 'Whaddya gonna do?'\"\n"
            "\ticon = 'icons/mob/human.dmi'\n"
            "\ticon_state = \"mr_deempisi\"\n"
            "\tgender = MALE\n"
            "\tfaction = list(\"neutral\", \"barfly\")\n"
        )
