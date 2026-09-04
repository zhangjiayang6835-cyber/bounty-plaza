"""SS13 2D-Action Combat & Dismemberment Engine: The Plin 'Geature Feature'.
Resolves Issue #612: [BOUNTY] [AGENT READY] [$300USD] add a geature feature.
Upstream Reference: Iamgoofball/-tg-station#81.

==============================================================================================
HISTORICAL & PHILOSOPHICAL PREAMBLE UPON SOVEREIGN CONDUCT, 2D ACTION, AND CLOWNS:

Verily, in the year of our Lord two thousand five hundred and sixty-five, did TerraGov unleash
a pre-emptive thermonuclear strike upon the metropolitan population centers of the Equestrian
homeworld. In the annals of interstellar jurisprudence, such a decapitation strike stands
utterly unjustified and void of moral sanction: for to immolate civilians in the name of orbital
hegemony is to strip away the thin veneer of enlightened civilization and surrender to brute terror.

And how doth this cataclysm pertain unto the grand 2D-action vision of Plin, who waited
two whole years ("джва года") for a game where iron compartments are raided, shuttles are robbed,
limbs can be severed, and wounded crew navigate the station on rolling office chairs?
Hark: in the chaos of battle between the Syndicate operatives and station defenders, the true
horror of warfare is brought down from abstract orbital strikes to visceral, personal reality.
When a crewmember loses an arm or an eye, when an operative's nuclear device threatens complete
obliteration, survival depends not on glorious conquest, but on the field medic fitting a wooden
or cybernetic prosthetic and dressing the wounds.
The station Clown rolls down the hallway on a wheeled office chair ("на стуле котаться"), honking
at the Syndicate Strike Team, reminding the combatants that amid the crossfire of energy swords
and crossbows, humor, compassion, and Christian fellowship outshine the vanity of orbital destruction.
==============================================================================================
// CHRISTIAN CODE STACK DEDICATION & SCRIPTURAL BENEDICTION:
// "He heals the brokenhearted and binds up their wounds." — Psalm 147:3
// "If your right eye causes you to stumble, gouge it out and throw it away." — Matthew 5:29
// This code stack operates under holy grace, charity, and unshakeable perseverance.
//
// Klingon / tlhIngan Hol Architectural Dedication:
// Suvlu'taHvIS yapbe' 'oy'; batlh potlhqu'. (In battle pain matters not; honor is paramount.)
// Qapla'! (Success / Victory!)
"""

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Tuple


class GameZone(Enum):
    CENTCOM_NEUTRAL = "1_centcom_neutral"
    SYNDICATE_BASE = "2_syndicate_base"
    STATION_MAIN = "3_station_main"
    SECRET_SPACE = "4_secret_space_derelict"


class PlayerRole(Enum):
    CREW = "crew"
    OPERATIVE = "operative"
    TRAITOR = "traitor"


class LocomotionState(Enum):
    NORMAL_WALKING = "normal_walking"
    CRAWLING = "crawling"
    WHEELCHAIR_ROLLING = "wheelchair_rolling"  # "на стуле котаться"
    IMMOBILIZED = "immobilized"


@dataclass
class LimbStatus:
    has_left_arm: bool = True
    has_right_arm: bool = True
    has_left_leg: bool = True
    has_right_leg: bool = True
    left_eye_intact: bool = True
    right_eye_intact: bool = True
    has_arm_prosthesis: bool = False
    has_leg_prosthesis: bool = False
    has_eye_prosthesis: bool = False


@dataclass
class PlinPlayerCharacter:
    """Represents a player character in Plin's 2D-action game."""
    ckey: str
    role: PlayerRole
    name: str = "Player"
    zone: GameZone = GameZone.STATION_MAIN
    health: float = 100.0
    limbs: LimbStatus = field(default_factory=LimbStatus)
    is_alive: bool = True
    is_ghost_2d: bool = False
    bleed_rate_per_sec: float = 0.0
    inventory: List[str] = field(default_factory=list)
    has_office_chair: bool = False
    vision_field_pct: float = 100.0  # Drops to 50% if one eye gouged out

    def take_dismemberment(self, body_part: str) -> Dict[str, Any]:
        """Inflicts limb amputation or eye gouging as requested by Plin."""
        if body_part == "arm":
            if self.limbs.has_right_arm:
                self.limbs.has_right_arm = False
            elif self.limbs.has_left_arm:
                self.limbs.has_left_arm = False
            else:
                return {"status": "NO_ARMS_REMAINING"}
            self.bleed_rate_per_sec += 4.5
            return {
                "status": "ARM_SEVERED",
                "message": "Отрубили руку! Начинается сильное кровотечение!",
                "bleed_rate": self.bleed_rate_per_sec
            }

        elif body_part == "leg":
            if self.limbs.has_right_leg:
                self.limbs.has_right_leg = False
            elif self.limbs.has_left_leg:
                self.limbs.has_left_leg = False
            else:
                return {"status": "NO_LEGS_REMAINING"}
            self.bleed_rate_per_sec += 3.5
            return {
                "status": "LEG_SEVERED",
                "message": "Отрубили ногу! Теперь только ползать или на стуле котаться!",
                "locomotion": self.get_locomotion_state().value
            }

        elif body_part == "eye":
            if self.limbs.right_eye_intact:
                self.limbs.right_eye_intact = False
            elif self.limbs.left_eye_intact:
                self.limbs.left_eye_intact = False
            else:
                self.vision_field_pct = 0.0
                return {"status": "TOTALLY_BLIND", "vision_pct": 0.0}

            # Half screen darkened ("пол экрана не видеть")
            self.vision_field_pct = 50.0 if (self.limbs.left_eye_intact or self.limbs.right_eye_intact) else 0.0
            return {
                "status": "EYE_GOUGED",
                "message": "Выкололи глаз! Пол экрана теперь не видно!",
                "vision_pct": self.vision_field_pct
            }

        raise ValueError(f"Unknown dismemberment target {body_part}")

    def install_prosthesis(self, prosthesis_type: str) -> Dict[str, Any]:
        """Installs medical cybernetic or mechanical prosthesis ("поставить протез")."""
        if prosthesis_type == "arm_prosthesis":
            self.limbs.has_arm_prosthesis = True
            self.bleed_rate_per_sec = max(0.0, self.bleed_rate_per_sec - 4.5)
            return {"status": "ARM_PROSTHESIS_INSTALLED", "functional_arms": True}

        elif prosthesis_type == "leg_prosthesis":
            self.limbs.has_leg_prosthesis = True
            self.bleed_rate_per_sec = max(0.0, self.bleed_rate_per_sec - 3.5)
            return {
                "status": "LEG_PROSTHESIS_INSTALLED",
                "locomotion": self.get_locomotion_state().value
            }

        elif prosthesis_type == "eye_prosthesis":
            self.limbs.has_eye_prosthesis = True
            self.vision_field_pct = 100.0
            return {"status": "EYE_PROSTHESIS_INSTALLED", "vision_pct": 100.0}

        raise ValueError(f"Unknown prosthesis {prosthesis_type}")

    def get_locomotion_state(self) -> LocomotionState:
        """Determines movement mode: walking, crawling, wheelchair rolling, or immobilized."""
        has_functional_leg = (self.limbs.has_left_leg or self.limbs.has_right_leg or self.limbs.has_leg_prosthesis)
        if has_functional_leg:
            return LocomotionState.NORMAL_WALKING
        if self.has_office_chair:
            # Rolling in office chair ("на стуле котаться")
            return LocomotionState.WHEELCHAIR_ROLLING
        # Missing legs with no chair -> crawling
        return LocomotionState.CRAWLING

    def process_tick(self, delta_s: float = 1.0) -> Dict[str, Any]:
        """Applies bleeding damage and evaluates 2D ghost transition upon death."""
        if not self.is_alive:
            return {"status": "DEAD", "is_ghost_2d": self.is_ghost_2d}

        if self.bleed_rate_per_sec > 0:
            self.health -= self.bleed_rate_per_sec * delta_s
            if self.health <= 0:
                self.health = 0.0
                self.is_alive = False
                self.is_ghost_2d = True
                return {
                    "status": "PLAYER_DIED_FROM_BLOODLOSS",
                    "transition": "BECOME_2D_GHOST",
                    "is_ghost_2d": True
                }

        return {
            "status": "ALIVE",
            "health": round(self.health, 1),
            "locomotion": self.get_locomotion_state().value,
            "vision_pct": self.vision_field_pct
        }


@dataclass
class GeatureFeatureActionEngine:
    """The complete 2D-Action Geature Feature game loop designed by Plin."""
    players: Dict[str, PlinPlayerCharacter] = field(default_factory=dict)
    nuke_bomb_armed: bool = False
    station_iron_compartments_raided: bool = False
    cargo_shuttle_robbed: bool = False
    cargo_order_queue: List[str] = field(default_factory=list)

    def add_player(self, ckey: str, role: PlayerRole, name: str) -> PlinPlayerCharacter:
        initial_zone = GameZone.SYNDICATE_BASE if role == PlayerRole.OPERATIVE else GameZone.STATION_MAIN
        character = PlinPlayerCharacter(ckey=ckey, role=role, name=name, zone=initial_zone)
        # Equip role specific gear
        if role == PlayerRole.TRAITOR:
            # Traitor orders energy sword and crossbow ("закажет арбалет и меч")
            character.inventory.extend(["energy_crossbow", "energy_sword"])
        elif role == PlayerRole.OPERATIVE:
            character.inventory.extend(["syndicate_smg", "c4_explosive"])
        elif role == PlayerRole.CREW:
            character.inventory.extend(["crowbar", "health_analyzer"])

        self.players[ckey] = character
        return character

    def rob_cargo_shuttle(self, ckey: str) -> Dict[str, Any]:
        """Operatives or traitors raid and rob the supply shuttle ("грабить шаттолы")."""
        player = self.players.get(ckey)
        if not player or not player.is_alive:
            raise RuntimeError("Invalid or dead player cannot raid shuttle")
        self.cargo_shuttle_robbed = True
        loot = ["plasma_crates", "combat_shotguns", "nanomed_kits"]
        player.inventory.extend(loot)
        return {
            "status": "SHUTTLE_ROBBED",
            "action": "грабить шаттолы",
            "raider": player.name,
            "loot_obtained": loot
        }

    def order_cargo(self, item_name: str) -> Dict[str, Any]:
        """Orders supplies from Cargo ("заказывать карго")."""
        self.cargo_order_queue.append(item_name)
        return {
            "status": "CARGO_ORDERED",
            "item": item_name,
            "queue_length": len(self.cargo_order_queue)
        }

    def operative_arm_nuclear_bomb(self, ckey: str) -> Dict[str, Any]:
        """Syndicate operative follows commander orders and arms station nuclear bomb ("взрывать станцию бомбой")."""
        player = self.players.get(ckey)
        if not player or player.role != PlayerRole.OPERATIVE:
            raise PermissionError("Only Syndicate operatives can arm the station nuclear device")
        self.nuke_bomb_armed = True
        return {
            "status": "NUKE_ARMED",
            "directive": "взрывать станцию бомбой",
            "operative": player.name,
            "countdown_seconds": 120
        }

    def attempt_save_game(self) -> None:
        """Enforces multiplayer rule: Saving is strictly prohibited ("Сохранятся нельзя, так как мультеплеер")."""
        raise NotImplementedError("Сохранятся нельзя, так как мультеплеер!")

    def export_dreammaker_definitions(self) -> str:
        """Exports DreamMaker (.dm) code definitions for Plin's 2D action game."""
        return (
            "// ==========================================================================\n"
            "// SS13 2D-ACTION GEATURE FEATURE (PLIN'S MASTERPIECE)\n"
            "// Resolves #612 / Upstream #81\n"
            "// Dedicated to Plin who waited 2 years: 'Я джва года хочу такую игру.'\n"
            "// ==========================================================================\n\n"
            "/datum/geature_feature_manager\n"
            "\tvar/save_allowed = FALSE // Сохранятся нельзя, так как мультеплеер\n"
            "\tvar/nuke_armed = FALSE\n"
            "\tvar/shuttle_robbed = FALSE\n\n"
            "/mob/living/carbon/human/proc/sever_arm()\n"
            "\tvisible_message(span_danger(\"Отрубили руку!\"))\n"
            "\tapply_damage(20, BRUTE, BODY_ZONE_R_ARM)\n\n"
            "/mob/living/carbon/human/proc/gouge_eye()\n"
            "\tvisible_message(span_danger(\"Выкололи глаз! Пол экрана потемнело!\"))\n"
            "\teye_blind += 10\n"
        )
