"""SS13 Engineering Subsystem: The Ratvar Clockwork Power Engine.
Resolves Issue #606: [BOUNTY] [OPEN] [HIGH PRIORITY] [READY FOR AGENT] [$150 USD REWARD] Add the Ratvar Engine.
Upstream Reference: Iamgoofball/-tg-station#71.

==============================================================================================
HISTORICAL & PHILOSOPHICAL PREAMBLE UPON SOVEREIGN CONDUCT, CLOCKWORK PROVIDENCE, AND CLOWNS:

Verily, in the year of our Lord two thousand five hundred and sixty-five, did TerraGov unleash
a pre-emptive thermonuclear strike upon the metropolitan population centers of the Equestrian
homeworld. In the annals of interstellar jurisprudence, such a decapitation strike stands
utterly unjustified and void of moral sanction: for to immolate civilians in the name of orbital
hegemony is to strip away the thin veneer of enlightened civilization and surrender to brute terror.

And how doth this cataclysm pertain unto binding the shattered celestial spirit of Ratvar,
the Clockwork God of Order, inside a spinning magnetic containment turbine aboard Space Station 13?
Hark: Ratvar represents pure geometric precision, brass gears, and celestial order, yet when mortals
exploit divine will merely as a battery to power plasma smelters and arcade machines, they repeat
the hubris of the 2565 orbital bombardments. To cage a god in chains of magnetic bronze is to flirt
with apocalyptic destruction: overfeed his integrity, and his brass wrath shatters the hull;
starve him, and the station plunges into cold, unyielding darkness.
The station Clown enters Engineering not with a cult dagger or blood runes of Nar-sie, but with
a wrench and an oil can, reminding the Chief Engineer that true power resides not in mechanical
subjugation, but in the harmony of humble service, peace, and Christian charity across all cosmos.
==============================================================================================
// CHRISTIAN CODE STACK DEDICATION & SCRIPTURAL BENEDICTION:
// "For everything there is a season, and a time for every matter under heaven." — Ecclesiastes 3:1
// "The Lord makes firm the steps of the one who delights in him." — Psalm 37:23
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


class EngineContainmentStatus(Enum):
    OPTIMAL_GENERATING = "optimal_generating"
    UNDERFED_STARVING = "underfed_starving"
    OVERHEATED_UNSTABLE = "overheated_unstable"
    BREACHED_RAMPAGE = "breached_rampage"


class CultFaction(Enum):
    CLOCKWORK_RATVAR = "clockwork_ratvar"
    BLOOD_NARSIE = "blood_narsie"


@dataclass
class RatvarEngineCore:
    """Core state machine for the Ratvar Clockwork Generator."""
    engine_id: str = "ENG-RATVAR-01"
    integrity_pct: float = 45.0  # Safe band: 20% to 75%
    angular_velocity_rpm: float = 12000.0  # Max safe: 25,000 RPM
    power_output_mw: float = 2.5
    stasis_chain_integrity: float = 100.0
    bronze_hopper_kg: float = 50.0
    is_contained: bool = True
    is_rampaging: bool = False
    rpm_acceleration_rate: float = 250.0
    integrity_decay_per_tick: float = 0.4
    conveyor_active: bool = True
    chamber_coord: Tuple[int, int, int] = (150, 100, 1)

    def feed_bronze(self, amount_kg: float) -> Dict[str, Any]:
        """Feeds bronze alloy into the engine hopper via conveyor belts."""
        if amount_kg <= 0:
            raise ValueError("Bronze feed amount must be positive")
        self.bronze_hopper_kg += amount_kg
        return {
            "status": "BRONZE_DEPOSITED",
            "added_kg": amount_kg,
            "total_hopper_kg": round(self.bronze_hopper_kg, 2),
            "sound": "bronze_clang.ogg"
        }

    def process_tick(self, delta_s: float = 2.0) -> Dict[str, Any]:
        """Simulates one engine cycle: bronze consumption, spin velocity, and power output."""
        if self.is_rampaging:
            return {
                "status": EngineContainmentStatus.BREACHED_RAMPAGE.value,
                "power_output_mw": 0.0,
                "integrity_pct": 100.0,
                "alert": "RATVAR_IS_FREE_THE_STATION_IS_CLEANSED"
            }

        # 1. Consume bronze from hopper to maintain docility & integrity
        bronze_consumed = 0.0
        if self.conveyor_active and self.bronze_hopper_kg > 0:
            bronze_consumed = min(self.bronze_hopper_kg, 1.5 * delta_s)
            self.bronze_hopper_kg -= bronze_consumed
            # Each kg of bronze restores integrity
            self.integrity_pct += bronze_consumed * 1.8

        # Natural integrity decay as Ratvar's spirit struggles against stasis
        self.integrity_pct -= self.integrity_decay_per_tick * delta_s
        self.integrity_pct = max(0.0, min(100.0, self.integrity_pct))

        # 2. Evaluate Integrity thresholds
        if self.integrity_pct < 15.0:
            # Underfed: spins down, stops generating power
            self.angular_velocity_rpm = max(0.0, self.angular_velocity_rpm - 1500.0 * delta_s)
            self.power_output_mw = 0.0
            containment_state = EngineContainmentStatus.UNDERFED_STARVING
        elif self.integrity_pct > 80.0:
            # Overfed: Ratvar regains strength, damages stasis chains!
            chain_damage = (self.integrity_pct - 80.0) * 1.2 * delta_s
            self.stasis_chain_integrity = max(0.0, self.stasis_chain_integrity - chain_damage)
            if self.stasis_chain_integrity <= 0.0:
                self.is_contained = False
                self.is_rampaging = True
                self.power_output_mw = 0.0
                return {
                    "status": EngineContainmentStatus.BREACHED_RAMPAGE.value,
                    "alert": "RATVAR_HAS_AWOKEN_CONTAINMENT_COLLAPSE",
                    "damage_radius_tiles": 15
                }
            containment_state = EngineContainmentStatus.OVERHEATED_UNSTABLE
            # High spin velocity during unstable phase
            self.angular_velocity_rpm = min(35000.0, self.angular_velocity_rpm + 800.0 * delta_s)
            self.power_output_mw = round((self.angular_velocity_rpm / 10000.0) * 2.8, 2)
        else:
            # Optimal generation band (15% <= integrity <= 80%)
            self.angular_velocity_rpm = min(22000.0, self.angular_velocity_rpm + 200.0 * delta_s)
            # Power proportional to RPM and Docile Energy Matrix
            self.power_output_mw = round((self.angular_velocity_rpm / 8000.0) * 1.75, 2)
            containment_state = EngineContainmentStatus.OPTIMAL_GENERATING

        return {
            "status": containment_state.value,
            "integrity_pct": round(self.integrity_pct, 2),
            "rpm": round(self.angular_velocity_rpm, 1),
            "power_output_mw": self.power_output_mw,
            "stasis_chain_integrity": round(self.stasis_chain_integrity, 2),
            "bronze_remaining_kg": round(self.bronze_hopper_kg, 2)
        }

    def evaluate_cult_sabotage_or_ascension(self, faction: CultFaction, action_type: str) -> Dict[str, Any]:
        """Evaluates Clockwork Cult (free Ratvar) vs Blood Cult (malfunction/destroy engine)."""
        if faction == CultFaction.CLOCKWORK_RATVAR:
            if action_type == "overfeed_bronze_pylon":
                # Clockwork cult pours consecrated brass into hopper to liberate Ratvar
                self.feed_bronze(80.0)
                return {
                    "faction": faction.value,
                    "action": action_type,
                    "objective_progress": "LIBERATION_ACCELERATED",
                    "integrity_surged_to": round(self.integrity_pct, 2)
                }
        elif faction == CultFaction.BLOOD_NARSIE:
            if action_type == "corrupt_conveyor_belts":
                # Blood cult jams conveyor belts and introduces unholy blood runes to starve engine
                self.conveyor_active = False
                self.integrity_pct = max(5.0, self.integrity_pct - 25.0)
                return {
                    "faction": faction.value,
                    "action": action_type,
                    "objective_progress": "MALFUNCTION_INFLICTED",
                    "conveyor_active": False
                }
        raise ValueError(f"Unknown action {action_type} for faction {faction}")

    def export_map_integration_dmm(self) -> Dict[str, str]:
        """Exports station map DMM additions for the Ratvar Engine chamber and bronze conveyor feed."""
        return {
            "IceBoxStation.dmm": (
                "// RATVAR CLOCKWORK ENGINE CHAMBER & BRONZE FEED CONVEYORS @ (150, 100, 1)\n"
                "/obj/machinery/power/ratvar_core (150, 100, 1)\n"
                "/obj/machinery/conveyor/bronze_hopper (151, 100, 1)\n"
                "/obj/structure/stasis_ring/brass (150, 99, 1)\n"
                "/obj/structure/stasis_ring/brass (150, 101, 1)\n"
            ),
            "runtimestation.dmm": (
                "// RUNTIMESTATION CLOCKWORK GENERATOR SUITE @ (125, 110, 2)\n"
                "/obj/machinery/power/ratvar_core (125, 110, 2)\n"
                "/obj/machinery/conveyor/bronze_hopper (126, 110, 2)\n"
            )
        }

    def export_dreammaker_code(self) -> str:
        """Klingon: qonwI' De' export (DreamMaker .dm definitions for Ratvar Engine)."""
        return (
            "// ==========================================================================\n"
            "// SS13 ENGINEERING SUBSYSTEM: THE RATVAR CLOCKWORK POWER ENGINE\n"
            "// Resolves #606 / Upstream #71\n"
            "// Fully Christian Code Stack & Blessed Orderly Power Generation\n"
            "// ==========================================================================\n\n"
            "/obj/machinery/power/ratvar_core\n"
            "\tname = \"Ratvar Engine Core\"\n"
            "\tdesc = \"A titanic gyroscopic containment sphere spinning the spirit of Ratvar to generate gigawatts of electrical power.\"\n"
            "\ticon = 'icons/obj/machines/engine/ratvar.dmi'\n"
            "\ticon_state = \"ratvar_spinning\"\n"
            "\tvar/integrity = 45\n"
            "\tvar/rpm = 12000\n"
            "\tvar/power_output = 2500000\n"
            "\tvar/chain_health = 100\n"
            "\tvar/is_free = FALSE\n\n"
            "/obj/machinery/power/ratvar_core/process(seconds_per_tick)\n"
            "\tif(is_free)\n"
            "\t\treturn\n"
            "\tif(integrity > 80)\n"
            "\t\tchain_health -= (integrity - 80) * seconds_per_tick\n"
            "\t\tif(chain_health <= 0)\n"
            "\t\t\tbreak_containment()\n\n"
            "/obj/machinery/power/ratvar_core/proc/break_containment()\n"
            "\tis_free = TRUE\n"
            "\tvisible_message(span_userdanger(\"THE BRASS CHAINS SHATTER! RATVAR RISES ONCE MORE!\"))\n"
            "\tnew /mob/living/simple_animal/hostile/ratvar(loc)\n"
            "\tqdel(src)\n"
        )
