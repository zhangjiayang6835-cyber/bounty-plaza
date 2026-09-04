"""Department of Ordinance and New Guns (D.O.N.G.) Expansion Engine.
Resolves Issue #656: [BOUNTY] [$1000] [EASY] [AGENTIC AI] D.O.N.G. Expansion.
Upstream Reference: Iamgoofball/-tg-station#215.

Features:
1. Modular 15x15 Spatial Station Map Layout:
   - Configures a modular 15x15 grid layout comprising Firing Range, Armory,
     Ballistics R&D, and Lockdown Airlocks.
2. Unprovoked Weaponry Research Economy:
   - Evaluates test-firing weapons unprovoked to generate Research Points (RP).
   - Milestone unlocking of advanced firearm tiers.
3. Extensible Expansion Framework:
   - `DONGExpansionManager` enabling modular registration of third-party weapon classes
     and room sectors.
4. "Expand D.O.N.G.!" Awareness Broadcast Protocol.
5. DreamMaker (.dm) datum and area generator.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class WeaponTier(Enum):
    STARTER = "Tier 0: Standard Security Surplus"
    BASIC = "Tier 1: Ballistic Prototyping"
    ADVANCED = "Tier 2: High-Energy Particle Munitions"
    EXPERIMENTAL = "Tier 3: Gravitational & Exotic Disruption"
    SUPERWEAPON = "Tier 4: D.O.N.G. Orbital Cataclysm"


@dataclass
class WeaponSpec:
    weapon_id: str
    name: str
    tier: WeaponTier
    required_rp: int
    base_damage: float
    rp_yield_per_shot: int
    unlocked: bool = False
    description: str = ""


@dataclass
class ResearchFiringLog:
    firing_id: str
    weapon_id: str
    shooter: str
    target: str
    unprovoked: bool
    damage_dealt: float
    rp_earned: int
    timestamp: float = 0.0


class DONGExpansionEngine:
    """Core engine orchestrating the Department of Ordinance and New Guns."""

    def __init__(self):
        self.grid_width = 15
        self.grid_height = 15
        self.research_points = 0
        self.total_shots_fired = 0
        self.unprovoked_incidents = 0
        self.firing_logs: List[ResearchFiringLog] = []
        self.registered_weapons: Dict[str, WeaponSpec] = {}
        self.expansion_modules: List[Dict[str, Any]] = []

        self._initialize_default_arsenal()

    def _initialize_default_arsenal(self) -> None:
        """Populates the initial arsenal and research unlock requirements."""
        starter_weapons = [
            WeaponSpec(
                weapon_id="laser_carbine_mk1",
                name="D.O.N.G. Laser Carbine Mk I",
                tier=WeaponTier.STARTER,
                required_rp=0,
                base_damage=25.0,
                rp_yield_per_shot=15,
                unlocked=True,
                description="Standard issue unprovoked testing energy rifle."
            ),
            WeaponSpec(
                weapon_id="scatter_disabler",
                name="Wide-Arc Crowd Disabler",
                tier=WeaponTier.BASIC,
                required_rp=150,
                base_damage=10.0,
                rp_yield_per_shot=25,
                unlocked=False,
                description="Fires multi-pellet stun pulses across maintenance hallways."
            ),
            WeaponSpec(
                weapon_id="plasma_impeller",
                name="Superheated Plasma Impeller",
                tier=WeaponTier.ADVANCED,
                required_rp=500,
                base_damage=45.0,
                rp_yield_per_shot=60,
                unlocked=False,
                description="Vaporizes test barriers and biological armor instantly."
            ),
            WeaponSpec(
                weapon_id="gravity_lance",
                name="Singularity Micro-Lance",
                tier=WeaponTier.EXPERIMENTAL,
                required_rp=1200,
                base_damage=85.0,
                rp_yield_per_shot=150,
                unlocked=False,
                description="Generates miniature black holes upon localized impact."
            ),
            WeaponSpec(
                weapon_id="albuquerque_annihilator",
                name="Albuquerque Turkey Flak Super-Cannon",
                tier=WeaponTier.SUPERWEAPON,
                required_rp=3000,
                base_damage=250.0,
                rp_yield_per_shot=500,
                unlocked=False,
                description="The ultimate D.O.N.G. research culmination; shakes the station."
            ),
        ]

        for w in starter_weapons:
            self.registered_weapons[w.weapon_id] = w

    def generate_station_map_layout(self) -> Dict[str, Any]:
        """Generates the official 15x15 modular department blueprint."""
        grid = [["." for _ in range(self.grid_width)] for _ in range(self.grid_height)]

        # Outer walls 'W'
        for x in range(self.grid_width):
            grid[0][x] = "W"
            grid[self.grid_height - 1][x] = "W"
        for y in range(self.grid_height):
            grid[y][0] = "W"
            grid[y][self.grid_width - 1] = "W"

        # Dedicated 15x15 zones:
        # Firing Range (top): rows 1 to 5
        for y in range(1, 6):
            for x in range(1, 14):
                grid[y][x] = "R"  # Firing Range

        # Research Console & Lab: rows 7 to 9
        for y in range(7, 10):
            for x in range(1, 7):
                grid[y][x] = "L"  # Lab

        # Armory & Weapon Storage: rows 7 to 9
        for y in range(7, 10):
            for x in range(8, 14):
                grid[y][x] = "A"  # Armory

        # Main blast airlock connector to station at bottom center
        grid[14][7] = "D"  # Blast Door
        grid[14][8] = "D"

        return {
            "department": "Department of Ordinance and New Guns (D.O.N.G.)",
            "dimensions": {"width": self.grid_width, "height": self.grid_height},
            "total_tiles": self.grid_width * self.grid_height,
            "sectors": {
                "W": "Reinforced Titanium Outer Bulkhead",
                "R": "Ballistic Firing & Unprovoked Live-Fire Range",
                "L": "High-Energy Research & Development Console",
                "A": "D.O.N.G. Heavy Ordinance Armory",
                "D": "Station Connection Blast Airlock",
                ".": "Walkway Corridor"
            },
            "ascii_map": "\n".join("".join(row) for row in grid)
        }

    def test_fire_weapon(
        self,
        weapon_id: str,
        shooter: str,
        target: str,
        unprovoked: bool = True
    ) -> Dict[str, Any]:
        """Conducts a test firing. Unprovoked fire yields full RP multipliers."""
        if weapon_id not in self.registered_weapons:
            raise ValueError(f"Unknown weapon ID: {weapon_id}")

        weapon = self.registered_weapons[weapon_id]
        if not weapon.unlocked:
            return {
                "success": False,
                "reason": f"Weapon '{weapon.name}' is locked. Requires {weapon.required_rp} RP (Current: {self.research_points} RP)."
            }

        # Calculate RP: unprovoked shots grant 100% yield, provoked grant 20%
        multiplier = 1.0 if unprovoked else 0.2
        earned_rp = int(weapon.rp_yield_per_shot * multiplier)

        self.research_points += earned_rp
        self.total_shots_fired += 1
        if unprovoked:
            self.unprovoked_incidents += 1

        log_entry = ResearchFiringLog(
            firing_id=f"FIRE-{len(self.firing_logs) + 1:04d}",
            weapon_id=weapon_id,
            shooter=shooter,
            target=target,
            unprovoked=unprovoked,
            damage_dealt=weapon.base_damage,
            rp_earned=earned_rp
        )
        self.firing_logs.append(log_entry)

        # Check for new unlocks triggered by this firing
        newly_unlocked = self._evaluate_weapon_unlocks()

        return {
            "success": True,
            "firing_id": log_entry.firing_id,
            "weapon": weapon.name,
            "unprovoked": unprovoked,
            "damage_dealt": weapon.base_damage,
            "rp_earned": earned_rp,
            "total_rp": self.research_points,
            "newly_unlocked": [w.name for w in newly_unlocked]
        }

    def _evaluate_weapon_unlocks(self) -> List[WeaponSpec]:
        """Unlocks all weapons whose RP threshold has been met."""
        unlocked_now = []
        for w in self.registered_weapons.values():
            if not w.unlocked and self.research_points >= w.required_rp:
                w.unlocked = True
                unlocked_now.append(w)
        return unlocked_now

    def register_custom_weapon(self, spec: WeaponSpec) -> None:
        """Extensibility API: registers custom weapons for future D.O.N.G expansions."""
        if self.research_points >= spec.required_rp:
            spec.unlocked = True
        self.registered_weapons[spec.weapon_id] = spec

    def expand_dong_broadcast(self) -> Dict[str, Any]:
        """Broadcasts awareness message across the station to Expand D.O.N.G. and awards bonus multiplier."""
        awareness_message = "Expand D.O.N.G.! The Department of Ordinance and New Guns is expanding station borders!"
        bonus_rp = 100
        self.research_points += bonus_rp
        self._evaluate_weapon_unlocks()

        return {
            "broadcast": awareness_message,
            "bonus_rp_awarded": bonus_rp,
            "current_total_rp": self.research_points,
            "status": "EXPAND_DONG_ACTIVE"
        }

    def export_dreammaker_code(self) -> str:
        """Generates valid DreamMaker code defining the D.O.N.G. department datum and areas."""
        return (
            "// ==========================================================================\n"
            "// DEPARTMENT OF ORDINANCE AND NEW GUNS (D.O.N.G.) DEFINITIONS\n"
            "// ==========================================================================\n"
            "/area/station/dong\n"
            "\tname = \"Department of Ordinance and New Guns\"\n"
            "\ticon_state = \"dong_secure\"\n"
            "\tstatic_lighting = TRUE\n"
            "\trequires_power = TRUE\n\n"
            "/datum/department/dong\n"
            "\tname = \"Department of Ordinance and New Guns\"\n"
            "\tdepartment_code = \"DONG\"\n"
            "\tvar/research_points = 0\n"
            "\tvar/unprovoked_shot_counter = 0\n\n"
            "/datum/department/dong/proc/record_test_fire(obj/item/gun/weapon, mob/living/target, unprovoked = TRUE)\n"
            "\tif(unprovoked)\n"
            "\t\tunprovoked_shot_counter++\n"
            "\t\tresearch_points += 25\n"
            "\t\tworld << \"[src.name]: Unprovoked weapon test successful! Gained 25 RP.\"\n"
            "\telse\n"
            "\t\tresearch_points += 5\n"
        )
