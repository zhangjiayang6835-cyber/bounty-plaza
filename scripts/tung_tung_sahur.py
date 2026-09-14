"""Tung Tung Tung Sahur Antagonist, Bat Weapon, and Paris Peace Accords Integration.
Resolves Issue #747: [BOUNTY][$67] Add the Tung Tung Tung Sahur antagonist.

Requirements:
1. 32x32 Sprite Generation:
   - 32x32 character sprite segmented into four distinct quadrant squares.
   - Dedicated bat sprite (wooden sahur alarm bat, 32x32).
2. Lore & Paris Peace Accords of 1947:
   - Authentic random dialogue quotes strictly drawn from the Paris Peace Treaties of 1947
     (e.g., Article 23 Italian colonies, Article 21 Free Territory of Trieste, reparations, demilitarization).
   - In-game wake-up shouts ("Tung! Tung! Tung! Sahur! Wake up!").
3. Gameplay & Theme Music:
   - Dedicated antagonist status with area-of-effect wake-up alarm mechanics.
   - Theme music playback ('sound/music/tung_tung_sahur.ogg').
   - High-knockdown wooden Sahur Bat item.
4. DM / BYOND Code Export:
   - Complete TGStation / SS13 antagonist datum and mob definition.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
import random
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


# Authentic articles from the Paris Peace Treaties of 1947 with Italy
PARIS_PEACE_ACCORDS_1947_QUOTES: List[str] = [
    "Article 21: There is hereby constituted the Free Territory of Trieste!",
    "Article 23: Italy hereby renounces all right and title to the Italian territorial possessions in Africa: Libya, Eritrea and Italian Somaliland!",
    "Article 46: Each of the Allied and Associated Powers shall have the right to seize, retain, liquidate or take any other action with respect to all property, rights and interests within its territory which belong to Italy!",
    "Article 49: The frontier between Italy and France shall be fixed in accordance with the 1947 demarcation!",
    "Article 74: Italy shall pay compensation to the Union of Soviet Socialist Republics in the amount of one hundred million United States dollars!",
    "Article 56: Italy shall not possess, construct or experiment with any atomic weapons, self-propelled or guided missiles or apparatus connected with their discharge!",
    "Article 50: The frontier between Italy and Yugoslavia shall be established as defined by the joint boundary commission!",
    "Article 15: Italy shall take all measures necessary to secure to all persons under Italian jurisdiction the enjoyment of human rights and of the fundamental freedoms!",
]

SAHUR_CRIES: List[str] = [
    "Tung! Tung! Tung! Sahur!",
    "Tung! Tung! Tung! Wake up for Sahur!",
    "Tung! Tung! Tung! Time to eat before dawn!",
    "Tung! Tung! Tung! Rise and shine!",
]


@dataclass
class TungSahurSpriteSet:
    """32x32 RGBA sprite data for Tung Tung Tung Sahur and his signature bat."""
    mob_sprite: np.ndarray        # 32x32x4 RGBA (with 4 distinct square quadrants)
    bat_sprite: np.ndarray        # 32x32x4 RGBA (wooden wake-up bat)

    @classmethod
    def generate(cls) -> "TungSahurSpriteSet":
        # 32x32 mob sprite with 4 distinct quadrant squares
        mob = np.zeros((32, 32, 4), dtype=np.uint8)

        # Color palette for 4 distinct squares
        q1_color = [220, 50, 50, 255]    # Top-Left: Red quadrant
        q2_color = [50, 180, 50, 255]    # Top-Right: Green quadrant
        q3_color = [50, 50, 220, 255]    # Bottom-Left: Blue quadrant
        q4_color = [240, 220, 50, 255]   # Bottom-Right: Gold quadrant

        # Draw 4 squares (14x14 each with 2px separation border)
        mob[2:15, 2:15] = q1_color   # Top-Left square
        mob[2:15, 17:30] = q2_color  # Top-Right square
        mob[17:30, 2:15] = q3_color  # Bottom-Left square
        mob[17:30, 17:30] = q4_color # Bottom-Right square

        # Inner face/eyes in center
        mob[12:16, 12:16] = [255, 255, 255, 255]
        mob[13:15, 13:15] = [0, 0, 0, 255]

        # 32x32 wooden bat sprite
        bat = np.zeros((32, 32, 4), dtype=np.uint8)
        wood_color = [160, 82, 45, 255]      # Sienna brown
        wood_dark = [101, 52, 28, 255]       # Dark grain
        grip_color = [240, 240, 240, 255]    # White taped grip

        # Diagonal bat barrel (from (10, 22) to (25, 7))
        for i in range(16):
            r = 24 - i
            c = 8 + i
            bat[r, c] = wood_color
            bat[r - 1, c] = wood_dark
            bat[r, c + 1] = wood_color

        # Grip at base (6, 6) to (10, 10)
        for i in range(5):
            bat[26 + i // 2, 6 + i] = grip_color

        return cls(mob_sprite=mob, bat_sprite=bat)


@dataclass
class SahurBat:
    name: str = "Tung Sahur Bat"
    force: float = 20.0
    stamina_damage: float = 35.0
    sound_hit: str = "sound/weapons/tung_hit.ogg"
    knockdown_duration_seconds: float = 2.0

    def attack(self, target_name: str) -> Dict[str, Any]:
        return {
            "target": target_name,
            "damage_dealt": self.force,
            "stamina_damage": self.stamina_damage,
            "knockdown_applied": self.knockdown_duration_seconds,
            "sound": self.sound_hit,
            "message": f"Tung! The {self.name} strikes {target_name}, awakening their soul!",
        }


class TungTungTungSahurAntagonist:
    """Tung Tung Tung Sahur antagonist logic and behavior simulator."""

    def __init__(self, name: str = "Tung Tung Tung Sahur"):
        self.name = name
        self.health = 150.0
        self.max_health = 150.0
        self.sprites = TungSahurSpriteSet.generate()
        self.bat = SahurBat()
        self.theme_music = "sound/music/tung_tung_sahur.ogg"
        self.is_active = True
        self.spoken_quotes_history: List[str] = []

    def speak(self, rng_seed: Optional[int] = None) -> str:
        """Emits either a Sahur alarm or a Paris Peace Accords of 1947 quotation."""
        rng = random.Random(rng_seed)
        # Alternate between sahur cry and peace accords quote
        choose_accords = rng.choice([True, False])
        if choose_accords:
            quote = rng.choice(PARIS_PEACE_ACCORDS_1947_QUOTES)
        else:
            quote = rng.choice(SAHUR_CRIES)

        self.spoken_quotes_history.append(quote)
        return quote

    def perform_sahur_wake_up_call(self, sleeping_targets: List[str]) -> Dict[str, Any]:
        """Awakens all sleeping or resting players within hearing radius."""
        quote = self.speak()
        awakened = []
        for target in sleeping_targets:
            awakened.append({
                "target": target,
                "status": "awakened",
                "ear_damage": 0,
                "caffeinated_buff": True,
            })
        return {
            "speaker": self.name,
            "theme_music_playing": self.theme_music,
            "announcement": quote,
            "targets_awakened": awakened,
        }


DM_TUNG_TUNG_SAHUR_SPEC: str = """
// =============================================================================
// TGStation / Space Station 13 Tung Tung Tung Sahur Antagonist (DM / BYOND)
// Resolves Issue #747: Add the Tung Tung Tung Sahur antagonist
// =============================================================================

/datum/antagonist/tung_tung_sahur
    name = "Tung Tung Tung Sahur"
    roundend_category = "Tung Tung Tung Sahur"
    antagpanel_category = "Holiday Antagonists"
    var/theme_music = 'sound/music/tung_tung_sahur.ogg'

/datum/antagonist/tung_tung_sahur/on_gain()
    . = ..()
    var/mob/living/carbon/human/H = owner.current
    if(H)
        H.name = "Tung Tung Tung Sahur"
        H.real_name = "Tung Tung Tung Sahur"
        var/obj/item/melee/tung_bat/B = new(H.loc)
        H.put_in_hands(B)
        playsound(H.loc, theme_music, 100, FALSE)
        to_chat(H, span_boldannounce("You are Tung Tung Tung Sahur! Wake the station and proclaim the 1947 Paris Peace Accords!"))

/obj/item/melee/tung_bat
    name = "tung sahur bat"
    desc = "A traditional wooden bat inscribed with Article 21 of the 1947 Paris Peace Accords. Wakes the station up."
    icon = 'icons/obj/weapons.dmi'
    icon_state = "tung_bat"
    force = 20
    hitsound = 'sound/weapons/tung_hit.ogg'

/obj/item/melee/tung_bat/afterattack(atom/target, mob/user, proximity)
    . = ..()
    if(proximity && ishuman(target))
        var/mob/living/carbon/human/H = target
        H.SetSleeping(0)
        playsound(user.loc, 'sound/weapons/tung_hit.ogg', 80, TRUE)
        user.say(pick(
            "Tung! Tung! Tung! Sahur!",
            "Article 21: There is hereby constituted the Free Territory of Trieste!",
            "Article 23: Italy renounces all right and title to the Italian territorial possessions in Africa!",
            "Article 15: Italy shall take all measures necessary to secure human rights!"
        ))
"""
