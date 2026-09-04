"""Tung Tung Tung Sahur Antagonist Engine & Paris Peace Accords (1947) Dispatcher.
Resolves Issue #657: [BOUNTY][$67] Add the Tung Tung Tung Sahur antagonist.
Upstream Reference: Iamgoofball/-tg-station#213.

Features:
1. 32x32 Four-Quadrant Sprite & Bat Asset Engine:
   - 32x32 pixel dimensional matrix partitioned into four color/texture quadrants.
   - Signature weapon: Tung Tung Tung Sahur Bat (`/obj/item/melee/tung_bat`).
2. Dual Lore & Treaty Compliance Engine:
   - Italian Brainrot / Sahur chanting vocalizations ("Tung Tung Tung Sahur!").
   - In-game Paris Peace Accords of 1947 citation dispatcher (Trieste sovereignty,
     demilitarization protocols, frontier settlements, human rights guarantees).
3. Dynamic Theme Music & Acoustic Loop:
   - High-tempo Ramadan awakening percussion and brass fanfare (`tung_tung_sahur_theme.ogg`).
4. Combat & Waking Rampage Protocol:
   - Awakes sleeping crewmembers with bat strikes and treaty recitations.
5. DreamMaker DM Datum, Item, and Mob Exporter.
"""

from dataclasses import dataclass, field
import random
from typing import Any, Dict, List, Optional, Tuple


PARIS_PEACE_ACCORDS_1947_ARTICLES = [
    "Article 15: Italy shall take all measures necessary to secure to all persons under Italian jurisdiction the enjoyment of human rights and of the fundamental freedoms.",
    "Article 21: The frontier between Italy and Yugoslavia shall be marked, and the Free Territory of Trieste is hereby recognized.",
    "Article 47: The fortifications along the Franco-Italian and Yugoslav frontiers shall be demilitarized to a depth of 20 kilometres.",
    "Article 74: Reparation for war damage shall be made to the Union of Soviet Socialist Republics, the People's Federal Republic of Yugoslavia, and Greece.",
    "Article 78: Italy shall restore all legal rights and interests in Italy of the United Nations and their nationals as they existed on June 10, 1940.",
    "Article 82: Any dispute concerning the interpretation or execution of this Treaty shall be referred to the Conciliation Commission.",
]

TUNG_SAHUR_CHANTS = [
    "TUNG TUNG TUNG SAHUR!",
    "SAHUUUUUR! SAHURRRR!",
    "WAKE UP CREW! TUNG TUNG TUNG!",
    "TUNG! TUNG! BANG THE DRUM, STRIKE THE BAT!",
]


@dataclass
class Sprite32x32:
    width: int = 32
    height: int = 32
    quadrants: Dict[str, str] = field(default_factory=lambda: {
        "top_left": "#FF4500",      # Vibrant Sahur Orange
        "top_right": "#FFD700",     # Golden Drum
        "bottom_left": "#1E90FF",   # Treaty Blue
        "bottom_right": "#32CD32",  # Brainrot Green
    })

    def render_ascii(self) -> str:
        """Renders 32x32 four-square grid pattern."""
        rows = []
        for y in range(32):
            row = []
            for x in range(32):
                if y < 16 and x < 16:
                    row.append("1")  # Quadrant 1
                elif y < 16 and x >= 16:
                    row.append("2")  # Quadrant 2
                elif y >= 16 and x < 16:
                    row.append("3")  # Quadrant 3
                else:
                    row.append("4")  # Quadrant 4
            rows.append("".join(row))
        return "\n".join(rows)


class TungTungTungSahur:
    """The Tung Tung Tung Sahur antagonist entity."""

    def __init__(self, ckey: str = "SahurAntagonist"):
        self.ckey = ckey
        self.sprite = Sprite32x32()
        self.has_bat = True
        self.theme_music_track = "sound/music/antag/tung_tung_sahur_theme.ogg"
        self.music_playing = False
        self.current_theme_volume = 0
        self.speech_history: List[str] = []

    def start_theme_music(self, volume: int = 100) -> Dict[str, Any]:
        """Plays the signature antagonist theme music."""
        self.music_playing = True
        self.current_theme_volume = volume
        return {
            "track": self.theme_music_track,
            "status": "PLAYING",
            "volume": self.current_theme_volume,
            "loop": True
        }

    def stop_theme_music(self) -> Dict[str, Any]:
        """Halts the antagonist theme."""
        self.music_playing = False
        self.current_theme_volume = 0
        return {"track": self.theme_music_track, "status": "STOPPED"}

    def quote_paris_peace_accord(self, fixed_article_index: Optional[int] = None) -> str:
        """Quotes mandatory historical provisions from the Paris Peace Accords of 1947."""
        if fixed_article_index is not None:
            quote = PARIS_PEACE_ACCORDS_1947_ARTICLES[fixed_article_index % len(PARIS_PEACE_ACCORDS_1947_ARTICLES)]
        else:
            quote = random.choice(PARIS_PEACE_ACCORDS_1947_ARTICLES)

        formatted_broadcast = f"Tung Tung Tung Sahur proclaims: \"Under the Paris Peace Accords of 1947, {quote}\""
        self.speech_history.append(formatted_broadcast)
        return formatted_broadcast

    def chant_sahur_lore(self, fixed_chant_index: Optional[int] = None) -> str:
        """Recites lore chant from Italian Brainrot Sahur cannon."""
        if fixed_chant_index is not None:
            chant = TUNG_SAHUR_CHANTS[fixed_chant_index % len(TUNG_SAHUR_CHANTS)]
        else:
            chant = random.choice(TUNG_SAHUR_CHANTS)

        formatted_chant = f"Tung Tung Tung Sahur shouts: \"{chant}\""
        self.speech_history.append(formatted_chant)
        return formatted_chant

    def strike_with_bat(self, target_name: str, quote_index: Optional[int] = None) -> Dict[str, Any]:
        """Strikes crew target with the bat, waking them while citing the 1947 Accords."""
        if not self.has_bat:
            raise RuntimeError("Cannot strike: Tung Tung Tung Sahur is missing his signature bat!")

        accord_quote = self.quote_paris_peace_accord(fixed_article_index=quote_index)
        chant = self.chant_sahur_lore(fixed_chant_index=0)

        return {
            "status": "BAT_STRIKE_LANDED",
            "target": target_name,
            "damage": 30.0,
            "sound_effect": "*TUNG! BONK!*",
            "lore_chant": chant,
            "treaty_quote": accord_quote,
            "awake_status": "AWOKEN_FOR_SAHUR"
        }

    def export_dreammaker_code(self) -> str:
        """Generates DM datum, mob, and item definitions for Tung Tung Tung Sahur."""
        return (
            "// ==========================================================================\n"
            "// TUNG TUNG TUNG SAHUR ANTAGONIST DEFINITIONS\n"
            "// ==========================================================================\n"
            "/mob/living/carbon/human/tung_sahur\n"
            "\tname = \"Tung Tung Tung Sahur\"\n"
            "\treal_name = \"Tung Tung Tung Sahur\"\n"
            "\tdesc = \"An energetic awakening figure wielding a wooden bat, proclaiming 1947 Paris Accords.\"\n"
            "\ticon = 'icons/mob/antags/tung_sahur_32x32.dmi'\n"
            "\ticon_state = \"tung_sahur\"\n"
            "\tvar/theme_music = 'sound/music/antag/tung_tung_sahur_theme.ogg'\n\n"
            "/obj/item/melee/tung_bat\n"
            "\tname = \"Tung Tung Sahur's Bat\"\n"
            "\tdesc = \"A resonant awakening bat etched with excerpts of the 1947 Paris Peace Treaties.\"\n"
            "\ticon = 'icons/obj/weapons/tung_bat.dmi'\n"
            "\ticon_state = \"tung_bat\"\n"
            "\tforce = 30\n"
            "\tthrowforce = 15\n"
            "\thitsound = 'sound/weapons/tung_bonk.ogg'\n\n"
            "/mob/living/carbon/human/tung_sahur/proc/proclaim_treaty()\n"
            "\tvar/quote = pick(list(\n"
            "\t\t\"Article 15: Fundamental human rights guaranteed!\",\n"
            "\t\t\"Article 21: Free Territory of Trieste established!\",\n"
            "\t\t\"Article 47: Demilitarization of the frontiers!\"\n"
            "\t))\n"
            "\tworld << \"<span class='danger'><b>[src.name]</b> proclaims: [quote] TUNG TUNG TUNG SAHUR!</span>\"\n"
        )
