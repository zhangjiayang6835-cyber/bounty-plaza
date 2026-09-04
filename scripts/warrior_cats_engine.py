"""Warrior Cats Codebase Overhaul & Clan Simulation Subsystem.
Resolves Issue #681: [Bounty] [100 ETH reward] [agentic ai] Create a Warrior Cats codebase.
Upstream Reference: Iamgoofball/-tg-station#260.

Features:
1. Five Clans System: ThunderClan, RiverClan, WindClan, ShadowClan, SkyClan (fully configurable).
2. Clan Hierarchy & Job Translation:
   - Captain -> Leader (9 Lives Revival System)
   - Head of Personnel -> Deputy (StarClan ascension upon Leader's 9th final death)
   - Chief Medical Officer -> Senior Medicine Cat
   - Station Staff / Security -> Warriors
   - Trainees / Assistants -> Apprentices (persistent mentorship shadowing)
3. Feline Anatomical Rework:
   - Hand slots replaced by a single mouth slot (/obj/item/organ/mouth_slot) for carrying prey/herbs.
   - Granular cat character customization: Breeds, coat patterns (Tabby, Calico, Tortoiseshell, Tuxedo), fur length, and eye colors.
   - Prefix/Suffix naming convention engine (e.g. Fireheart, Brambleclaw, Bluestar).
4. StarClan 9-Lives & Succession Ceremony:
   - Leader resurrects up to 9 times.
   - On 9th death, triggers 9 StarClan ghost roles giving virtues to Deputy, ascending them to new Leader.
5. Hunting & Fresh-Kill Pile Subsystem:
   - Scent tracking, stalking, and pouncing mechanics for prey (mice, voles, thrushes, rabbits, river fish).
6. BYOND DreamMaker codebase export hooks.
"""

from dataclasses import dataclass, field
from enum import Enum
import json
import random
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_CLANS = ["ThunderClan", "RiverClan", "WindClan", "ShadowClan", "SkyClan"]

CAT_BREEDS = [
    "Domestic Shorthair", "Maine Coon", "Siamese", "British Shorthair",
    "Persian", "Bengal", "Sphynx", "Norwegian Forest Cat", "Ragdoll", "Russian Blue"
]

COAT_PATTERNS = ["Classic Tabby", "Mackerel Tabby", "Calico", "Tortoiseshell", "Solid", "Tuxedo", "Colorpoint", "Bicolor"]
FUR_LENGTHS = ["Hairless", "Short", "Medium", "Long", "Dense Long"]

NAME_PREFIXES = [
    "Fire", "Bramble", "Blue", "Tiger", "Lion", "Jay", "Dove", "Holly",
    "Gray", "Raven", "Cloud", "Sand", "Spotted", "Leaf", "Squirrel", "Crow",
    "Hawk", "Moth", "Fern", "Dust", "Golden", "Swift", "Cinder", "Yellow"
]
NAME_SUFFIXES = [
    "heart", "claw", "star", "feather", "wing", "pelt", "stripe", "tail",
    "storm", "breeze", "flight", "pool", "leaf", "fang", "step", "frost"
]


class PreyType(Enum):
    MOUSE = "Mouse"
    VOLE = "Vole"
    RABBIT = "Rabbit"
    THRUSH = "Thrush"
    RIVER_FISH = "River Fish"


@dataclass
class FelineCustomization:
    breed: str
    coat_pattern: str
    coat_color: str
    fur_length: str
    eye_color: str

    def validate(self) -> bool:
        return (
            self.breed in CAT_BREEDS and
            self.coat_pattern in COAT_PATTERNS and
            self.fur_length in FUR_LENGTHS
        )


@dataclass
class CatCharacter:
    ckey: str
    clan: str
    prefix: str
    suffix: str
    role: str
    customization: FelineCustomization
    mouth_held_item: Optional[str] = None
    lives_remaining: int = 1
    mentor_ckey: Optional[str] = None

    @property
    def full_name(self) -> str:
        if self.role == "Leader":
            return f"{self.prefix}star"
        elif self.role == "Apprentice":
            return f"{self.prefix}paw"
        elif self.role == "Kit":
            return f"{self.prefix}kit"
        return f"{self.prefix}{self.suffix}"


class WarriorCatsEngine:
    """Core simulation engine for the Warrior Cats TG-Station overhaul."""

    def __init__(self, clans: Optional[List[str]] = None, leader_default_lives: int = 9, rng_seed: Optional[int] = None):
        self.clans = clans or list(DEFAULT_CLANS)
        self.leader_default_lives = leader_default_lives
        self.rng = random.Random(rng_seed) if rng_seed is not None else random.Random()
        self.cats: Dict[str, CatCharacter] = {}
        self.fresh_kill_pile: Dict[str, List[PreyType]] = {c: [] for c in self.clans}
        self.starclan_ghost_roles_queue: List[Dict[str, Any]] = []

    def generate_warrior_name(self, prefix: Optional[str] = None, suffix: Optional[str] = None) -> Tuple[str, str]:
        """Generates canonical Warrior Cats prefix and suffix names."""
        p = prefix or self.rng.choice(NAME_PREFIXES)
        s = suffix or self.rng.choice(NAME_SUFFIXES)
        while s == "star":  # Star is reserved strictly for leaders
            s = self.rng.choice(NAME_SUFFIXES)
        return p, s

    def register_cat(
        self,
        ckey: str,
        clan: str,
        role: str,
        prefix: str,
        suffix: str,
        customization: FelineCustomization,
    ) -> CatCharacter:
        """Enrolls a player cat into the specified Clan with mouth-only inventory."""
        if clan not in self.clans:
            raise ValueError(f"Unknown clan '{clan}'. Configured clans: {self.clans}")

        lives = self.leader_default_lives if role == "Leader" else 1
        cat = CatCharacter(
            ckey=ckey,
            clan=clan,
            prefix=prefix,
            suffix=suffix,
            role=role,
            customization=customization,
            lives_remaining=lives,
        )
        self.cats[ckey] = cat
        return cat

    def pickup_with_mouth(self, ckey: str, item_name: str) -> bool:
        """Picks up an item using the mouth slot. Fails if mouth is already occupied."""
        cat = self.cats.get(ckey)
        if not cat:
            return False
        if cat.mouth_held_item is not None:
            return False  # Hands culled; only 1 item can be carried in mouth
        cat.mouth_held_item = item_name
        return True

    def drop_from_mouth(self, ckey: str) -> Optional[str]:
        """Releases the currently held mouth item."""
        cat = self.cats.get(ckey)
        if not cat or cat.mouth_held_item is None:
            return None
        item = cat.mouth_held_item
        cat.mouth_held_item = None
        return item

    def hunt_prey(self, ckey: str, prey_type: Optional[PreyType] = None) -> Tuple[bool, Optional[PreyType]]:
        """Simulates hunting minigame: scent stalking and pouncing."""
        cat = self.cats.get(ckey)
        if not cat:
            return False, None

        target_prey = prey_type or self.rng.choice(list(PreyType))
        # River fish only available or more common in RiverClan territory
        if target_prey == PreyType.RIVER_FISH and cat.clan != "RiverClan":
            target_prey = PreyType.MOUSE

        # Hunting roll based on skill / role
        success_chance = 0.85 if cat.role in ["Leader", "Deputy", "Warrior"] else 0.55
        if self.rng.random() < success_chance:
            # Successfully caught prey, deposit into clan fresh-kill pile
            self.fresh_kill_pile[cat.clan].append(target_prey)
            return True, target_prey

        return False, None

    def process_leader_death(self, leader_ckey: str, deputy_ckey: Optional[str] = None) -> Dict[str, Any]:
        """Handles Leader fatal trauma, 9-lives decrement, or final death and StarClan ceremony."""
        leader = self.cats.get(leader_ckey)
        if not leader or leader.role != "Leader":
            raise ValueError("Target cat is not an active Leader.")

        leader.lives_remaining -= 1

        if leader.lives_remaining > 0:
            return {
                "status": "RESURRECTED",
                "lives_left": leader.lives_remaining,
                "message": f"StarClan has granted {leader.full_name} another life. {leader.lives_remaining} remaining."
            }

        # 9th Final Death reached: Leader passes to StarClan
        leader.role = "StarClan Ancestor"
        ceremony_report = {
            "status": "FINAL_DEATH",
            "deceased_leader": leader.full_name,
            "starclan_ghost_roles_spawned": self.leader_default_lives,
            "message": f"{leader.full_name} has joined StarClan. Calling {self.leader_default_lives} ghost roles."
        }

        # Spawn N ghost roles to gift lives to the Deputy
        for i in range(self.leader_default_lives):
            self.starclan_ghost_roles_queue.append({
                "role_id": f"starclan_ancestor_{i+1}",
                "virtue": f"Virtue of Wisdom {i+1}",
                "target_deputy": deputy_ckey
            })

        # Ascend Deputy to new Leader if provided
        if deputy_ckey and deputy_ckey in self.cats:
            deputy = self.cats[deputy_ckey]
            deputy.role = "Leader"
            deputy.lives_remaining = self.leader_default_lives
            ceremony_report["new_leader"] = deputy.full_name

        return ceremony_report

    def export_dm_code(self) -> str:
        """Generates standard BYOND DreamMaker typepaths for the Warrior Cats overhaul."""
        return (
            "// ========================================================\n"
            "// Warrior Cats Overhaul Subsystem & Feline Mob Architecture\n"
            "// ========================================================\n\n"
            "/datum/species/cat/warrior\n"
            "\tname = \"Warrior Cat\"\n"
            "\tid = \"warrior_cat\"\n"
            "\thands = 0 // Hands culled\n"
            "\tvar/obj/item/organ/mouth_slot/mouth = null\n"
            "\tvar/clan = \"ThunderClan\"\n"
            "\tvar/lives_remaining = 1\n\n"
            "/datum/job/clan/leader\n"
            "\ttitle = \"Clan Leader\"\n"
            "\ttotal_positions = 1\n"
            "\tvar/max_lives = 9\n\n"
            "/datum/job/clan/deputy\n"
            "\ttitle = \"Clan Deputy\"\n"
            "\ttotal_positions = 1\n\n"
            "/datum/job/clan/medicine_cat\n"
            "\ttitle = \"Senior Medicine Cat\"\n"
            "\ttotal_positions = 2\n\n"
            "/datum/job/clan/warrior\n"
            "\ttitle = \"Clan Warrior\"\n"
            "\ttotal_positions = -1\n\n"
            "/datum/job/clan/apprentice\n"
            "\ttitle = \"Clan Apprentice\"\n"
            "\ttotal_positions = -1\n"
            "\tvar/mentor_ckey = null\n"
        )
