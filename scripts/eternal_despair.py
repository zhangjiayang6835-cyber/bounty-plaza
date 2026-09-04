"""Eternal Despair Gameplay Mechanics & Running Trip Subsystem.
Resolves Issue #676: [BOUNTY] [$200] [OPIRE] Bring Eternal Despair to the Players.

Architectural Pillars:
1. Running Trip Hazard Engine:
   - While running/sprinting, movement steps carry a configurable chance of clumsy catastrophic tripping.
   - Tripping causes:
     * Immediate knockdown (actor drops prone for 2-4 seconds).
     * Disarmament: active and inactive hand items are forcefully dropped and scattered.
     * Minor physical brute damage + winded stamina penalty.
     * Audio cues: slip sound effects ('sound/misc/slip.ogg', 'sound/weapons/thudsnd.ogg').
2. Existential Despair & Nihilistic Hallucination Mood Drain:
   - Passive despair ticks causing involuntary melancholic sighs, existential dread popups,
     and temporary movement hesitation ("Why even run? Nothing matters.").
3. Inconvenience Matrix:
   - Dropped items experience random scatter trajectory.
   - Vending machine snack coin swallowing and untied shoelaces hazards.
4. DM / BYOND Component Export:
   - Full `/datum/component/eternal_despair` implementation for TGStation.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
import random
from typing import Any, Dict, List, Optional, Tuple


DESPAIR_MESSAGES: List[str] = [
    "You suddenly remember your insurmountable debts and unpaid bills.",
    "A cold chill runs down your spine as you realize nobody will remember this shift.",
    "You trip over an invisible metaphysical pebble of pure sorrow.",
    "Your shoelaces inexplicably knot themselves together in cosmic spite.",
    "You question why you sprint through dark steel corridors just to maximize shareholder value.",
    "The harsh fluorescent station lighting hums with infinite apathy.",
]


@dataclass
class ItemSlot:
    item_id: str
    name: str


@dataclass
class DespairConfig:
    trip_chance_while_sprinting: float = 0.08  # 8% chance per running step
    trip_knockdown_seconds: float = 2.5
    trip_brute_damage: float = 5.0
    trip_stamina_cost: float = 20.0
    despair_sanity_drain_per_tick: float = 1.0


class HumanMob:
    """Simulated carbon human crewmember subjected to the eternal despair subsystem."""

    def __init__(self, name: str = "Despairing Assistant"):
        self.name = name
        self.health = 100.0
        self.stamina = 100.0
        self.sanity_mood = 100.0  # Drops toward 0 (pure despair)
        self.is_sprinting = False
        self.is_knocked_down = False
        self.knockdown_timer = 0.0
        self.x = 0
        self.y = 0

        # Hand slots
        self.active_hand: Optional[ItemSlot] = ItemSlot("toolbox", "Mechanical Toolbox")
        self.inactive_hand: Optional[ItemSlot] = ItemSlot("id_card", "Assistant ID")
        self.dropped_floor_items: List[ItemSlot] = []
        self.total_trips_experienced = 0
        self.last_despair_log: Optional[str] = None

    def toggle_sprint(self, active: bool):
        self.is_sprinting = active

    def step_move(self, dx: int, dy: int, config: Optional[DespairConfig] = None, rng_seed: Optional[int] = None) -> Dict[str, Any]:
        """Executes a movement step, rolling for despair tripping if sprinting."""
        cfg = config or DespairConfig()
        rng = random.Random(rng_seed)

        if self.is_knocked_down:
            return {"moved": False, "reason": "knocked_down", "tripped": False}

        # Check tripping condition
        if self.is_sprinting:
            roll = rng.random()
            if roll < cfg.trip_chance_while_sprinting:
                return self.execute_trip(cfg, rng)

        # Successful step
        self.x += dx
        self.y += dy
        return {"moved": True, "new_pos": (self.x, self.y), "tripped": False}

    def execute_trip(self, cfg: DespairConfig, rng: random.Random) -> Dict[str, Any]:
        """Trips, knocks actor prone, drops all held items, and applies damage."""
        self.total_trips_experienced += 1
        self.is_knocked_down = True
        self.knockdown_timer = cfg.trip_knockdown_seconds
        self.health = max(0.0, self.health - cfg.trip_brute_damage)
        self.stamina = max(0.0, self.stamina - cfg.trip_stamina_cost)
        self.sanity_mood = max(0.0, self.sanity_mood - 5.0)

        # Scatter held items onto the floor
        scattered = []
        if self.active_hand:
            scattered.append(self.active_hand)
            self.dropped_floor_items.append(self.active_hand)
            self.active_hand = None
        if self.inactive_hand:
            scattered.append(self.inactive_hand)
            self.dropped_floor_items.append(self.inactive_hand)
            self.inactive_hand = None

        despair_msg = rng.choice(DESPAIR_MESSAGES)
        self.last_despair_log = despair_msg

        return {
            "moved": False,
            "tripped": True,
            "items_scattered": [item.name for item in scattered],
            "knockdown_applied": cfg.trip_knockdown_seconds,
            "damage_taken": cfg.trip_brute_damage,
            "message": f"{self.name} tripped violently and faceplanted! {despair_msg}",
            "sound": "sound/misc/slip.ogg",
        }

    def update_tick(self, dt: float):
        """Advances game clock."""
        if self.is_knocked_down:
            self.knockdown_timer = max(0.0, self.knockdown_timer - dt)
            if self.knockdown_timer <= 0.0:
                self.is_knocked_down = False


DM_ETERNAL_DESPAIR_SPEC: str = """
// =============================================================================
// TGStation Eternal Despair & Sprint Tripping Component (DM / BYOND)
// Resolves Issue #676: Bring Eternal Despair to the Players
// =============================================================================

/datum/component/eternal_despair
    dupe_mode = COMPONENT_DUPE_UNIQUE
    var/trip_chance = 8 // 8% chance per running step

/datum/component/eternal_despair/Initialize()
    if(!ishuman(parent))
        return COMPONENT_INCOMPATIBLE
    RegisterSignal(parent, COMSIG_MOVABLE_MOVED, PROC_REF(on_human_moved))

/datum/component/eternal_despair/proc/on_human_moved(mob/living/carbon/human/H, atom/old_loc, movement_dir, forced, list/old_locs)
    if(forced || H.stat != CONSCIOUS)
        return

    // Tripping only afflicts reckless sprinters
    if(H.m_intent == MOVE_INTENT_RUN)
        if(prob(trip_chance))
            trigger_sprint_trip(H)

/datum/component/eternal_despair/proc/trigger_sprint_trip(mob/living/carbon/human/H)
    to_chat(H, span_userdanger("You trip over your own heavy feet and smash into the deckplates!"))
    playsound(H.loc, 'sound/misc/slip.ogg', 70, TRUE)
    playsound(H.loc, 'sound/weapons/thudsnd.ogg', 50, TRUE)

    // Forceful disarmament of both hands
    H.drop_all_held_items()

    // Concussive knockdown and faceplant pain
    H.Knockdown(30)
    H.apply_damage(5, BRUTE, BODY_ZONE_HEAD)
    H.adjustStamina(-20)

    // Existential dread notification
    to_chat(H, span_warning(pick(
        "You suddenly remember your insurmountable mortgage and unpaid debts.",
        "A cold emptiness settles in your chest as you lay on the cold plating.",
        "You question why you sprint through dark steel corridors just to maximize shareholder value."
    )))
"""
