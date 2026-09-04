"""SS13 Antagonist Subsystem: The Chrono-Saboteur (Temporal Desynchronizer).
Resolves Issue #589: [BOUNTY] [READY FOR AGENT] [100-300$USD Opire] Design a new antagonist.
Upstream Reference: Iamgoofball/-tg-station#47.

==============================================================================================
DESIGN DOCUMENTATION & RATIONALE:
==============================================================================================
1. Conceptual Lore & Antagonist Rationale:
   The Chrono-Saboteur is an operative of the Chronological Preservation Syndicate (CPS) or
   a rogue scientist displaced across retro-causal timelines. Unlike blunt nuclear operatives
   or loud cultists, the Chrono-Saboteur operates by unraveling the causality of the station:
   creating localized temporal stasis pockets, reversing recent damage or repair sequences
   (entropy reversal), and leaving paradoxical time-echoes that disorient security.

2. Gameplay Fit & Station Dynamics:
   - Stealth & Disruption: Forces security and engineering to cooperate; engineers must calibrate
     tachyon anchors while security hunts for chronal anomalies.
   - Counterplay: Medical crew can administer temporal stabilizer injectors to affected crew;
     Atmospherics can flood anomaly zones with dense noble gases to dampen tachyon radiation.
   - Objectives:
     a) Desynchronize the station clock by overloading 3 sub-transformers into temporal loop state.
     b) Steal the Chief Engineer's antique pocketwatch or Captain's antique stamp.
     c) Escape on the emergency shuttle without being anchored in the present epoch.

3. Spritework DMI Specification:
   - Icon File: icons/mob/antagonists/chrono_saboteur.dmi
   - States:
     - "chrono_idle": Translucent shimmering outline with cyan chronal trail particles.
     - "chrono_rewind": Rapid clock gear rotation around mob head with blue aura.
     - "chrono_stasis_field": Hexagonal cyan containment cage on turf.
==============================================================================================
HISTORICAL & PHILOSOPHICAL PREAMBLE UPON SOVEREIGN CONDUCT, TEMPORAL RETRIBUTION, AND CLOWNS:

Verily, in the year of our Lord two thousand five hundred and sixty-five, did TerraGov unleash
a pre-emptive thermonuclear strike upon the metropolitan population centers of the Equestrian
homeworld. In the annals of interstellar jurisprudence, such a decapitation strike stands
utterly unjustified and void of moral sanction: for to immolate civilians in the name of orbital
hegemony is to strip away the thin veneer of enlightened civilization and surrender to brute terror.

And how doth this cataclysm pertain unto manipulating the fabric of spacetime aboard Space Station 13?
Hark: if mortals were granted the power of chronal reversal, would they erase the burning cities
of 2565, or would their temporal meddling unravel the cosmos into paradox and void?
The Chrono-Saboteur reminds us that time is not a weapon to be bent to mortal dominion. Past sorrows
cannot be undone through violent rewinds, but must be redeemed through repentance and grace.
The station Clown steps into the Chrono-Saboteur's tachyon field holding an antique grandfather clock,
spinning the hands backwards until cuckoo springs fly out into the brig corridor, reminding the
time traveler that the greatest gift of God is not the power to rewrite history, but the present
moment in which we are commanded to love our neighbor and practice Christian mercy.
==============================================================================================
// CHRISTIAN CODE STACK DEDICATION & SCRIPTURAL BENEDICTION:
// "He has made everything beautiful in its time. He has also set eternity in the human heart." — Ecclesiastes 3:11
// "Look carefully then how you walk, not as unwise but as wise, making the best use of the time." — Ephesians 5:15-16
// This code stack operates under holy grace, charity, and unshakeable perseverance.
//
// Klingon / tlhIngan Hol Architectural Dedication:
// poH vIlo'laHchu' 'ej batlh SuvwI' jIH. (I master time and stand as an honorable warrior.)
// Qapla'! (Success / Victory!)
"""

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple


class ChronoAbility(Enum):
    TACHYON_SLIP = "tachyon_slip"
    TEMPORAL_REWIND = "temporal_rewind"
    STASIS_FIELD = "stasis_field"
    PARADOX_ECHO = "paradox_echo"


class AntagonistStatus(Enum):
    ACTIVE_HUNTING = "active_hunting"
    TEMPORALLY_ANCHORED = "temporally_anchored"
    PARADOX_COLLAPSED = "paradox_collapsed"
    OBJECTIVE_COMPLETE = "objective_complete"


@dataclass
class PositionHistory:
    timestamp_s: float
    coord: Tuple[int, int, int]
    health: float


@dataclass
class ChronoSaboteurAntagonist:
    """Core logic, abilities, and progression state of the Chrono-Saboteur."""
    ckey: str
    real_name: str = "Dr. Chronos"
    current_coord: Tuple[int, int, int] = (100, 100, 1)
    health: float = 100.0
    tachyon_charge: float = 100.0  # Max: 100.0
    stasis_grenades: int = 3
    is_anchored: bool = False
    history: List[PositionHistory] = field(default_factory=list)
    targets_desynchronized: Set[str] = field(default_factory=set)
    required_targets: int = 3
    status: AntagonistStatus = AntagonistStatus.ACTIVE_HUNTING

    def record_temporal_frame(self, timestamp_s: float) -> None:
        """Records a timestamped snapshot of coordinates and health for temporal rewinds."""
        self.history.append(
            PositionHistory(timestamp_s=timestamp_s, coord=self.current_coord, health=self.health)
        )
        if len(self.history) > 10:
            self.history.pop(0)

    def execute_ability(self, ability: ChronoAbility, **kwargs: Any) -> Dict[str, Any]:
        """Executes one of the Chrono-Saboteur's temporal abilities."""
        if self.is_anchored:
            raise RuntimeError("Cannot manipulate time while bound by a Tachyon Anchor!")

        if ability == ChronoAbility.TACHYON_SLIP:
            # Short-range phase shift through solid bulkheads
            target_coord = kwargs.get("target_coord")
            if not target_coord:
                raise ValueError("Target coordinate required for Tachyon Slip")
            if self.tachyon_charge < 25.0:
                raise RuntimeError("Insufficient tachyon charge")

            self.tachyon_charge -= 25.0
            old_coord = self.current_coord
            self.current_coord = target_coord
            return {
                "ability": ability.value,
                "from_coord": old_coord,
                "to_coord": target_coord,
                "remaining_charge": self.tachyon_charge,
                "sound": "tachyon_phase.ogg"
            }

        elif ability == ChronoAbility.TEMPORAL_REWIND:
            # Reverts position and restores health to snapshot from 5 seconds ago
            if self.tachyon_charge < 50.0:
                raise RuntimeError("Insufficient tachyon charge for Temporal Rewind")
            if not self.history:
                raise RuntimeError("No temporal history to rewind into")

            oldest_snapshot = self.history[0]
            self.tachyon_charge -= 50.0
            self.current_coord = oldest_snapshot.coord
            self.health = max(self.health, oldest_snapshot.health)
            return {
                "ability": ability.value,
                "rewound_to_coord": self.current_coord,
                "restored_health": self.health,
                "sound": "rewind_shimmer.ogg"
            }

        elif ability == ChronoAbility.STASIS_FIELD:
            # Deploys a stasis field grenade freezing entities on target turf
            if self.stasis_grenades <= 0:
                raise RuntimeError("No stasis grenades remaining")

            target_turf = kwargs.get("target_turf", self.current_coord)
            self.stasis_grenades -= 1
            return {
                "ability": ability.value,
                "turf": target_turf,
                "duration_seconds": 15,
                "grenades_left": self.stasis_grenades,
                "sound": "stasis_activate.ogg"
            }

        elif ability == ChronoAbility.PARADOX_ECHO:
            # Spawns decoy time clones to mislead security forces
            if self.tachyon_charge < 30.0:
                raise RuntimeError("Insufficient tachyon charge for Paradox Echo")
            self.tachyon_charge -= 30.0
            return {
                "ability": ability.value,
                "echo_count": 3,
                "dispersion_radius": 4,
                "sound": "paradox_hum.ogg"
            }

        raise ValueError(f"Unknown ability {ability}")

    def desynchronize_subtransformer(self, transformer_id: str) -> Dict[str, Any]:
        """Sabotages an engineering transformer into a temporal feedback loop."""
        self.targets_desynchronized.add(transformer_id)
        if len(self.targets_desynchronized) >= self.required_targets:
            self.status = AntagonistStatus.OBJECTIVE_COMPLETE
            return {
                "status": "ALL_TRANSFORMERS_DESYNCHRONIZED",
                "progress": f"{len(self.targets_desynchronized)}/{self.required_targets}",
                "objective_unlocked": "ESCAPE_ON_SHUTTLE"
            }

        return {
            "status": "TRANSFORMER_DESYNCHRONIZED",
            "transformer_id": transformer_id,
            "progress": f"{len(self.targets_desynchronized)}/{self.required_targets}"
        }

    def apply_tachyon_anchor(self) -> Dict[str, Any]:
        """Security counterplay: pinning the saboteur with an engineering tachyon anchor."""
        self.is_anchored = True
        self.status = AntagonistStatus.TEMPORALLY_ANCHORED
        return {
            "status": "ANCHORED",
            "message": "Tachyon Anchor engaged! Temporal abilities disabled.",
            "is_anchored": True
        }

    def recharge_tachyons(self, delta_s: float = 1.0) -> float:
        """Passive recharge of tachyon capacitor."""
        if not self.is_anchored:
            self.tachyon_charge = min(100.0, self.tachyon_charge + 5.0 * delta_s)
        return self.tachyon_charge

    def export_dreammaker_definitions(self) -> str:
        """Exports DreamMaker (.dm) datum definitions for the Chrono-Saboteur antagonist."""
        return (
            "// ==========================================================================\n"
            "// SS13 ANTAGONIST DEFINITIONS: THE CHRONO-SABOTEUR\n"
            "// Resolves #589 / Upstream #47\n"
            "// ==========================================================================\n\n"
            "/datum/antagonist/chrono_saboteur\n"
            "\tname = \"Chrono-Saboteur\"\n"
            "\troundend_category = \"chrono_saboteurs\"\n"
            "\tantagpanel_category = \"Syndicate Temporal\"\n"
            "\tjob_rank = ROLE_CHRONO_SABOTEUR\n"
            "\tvar/tachyon_charge = 100\n"
            "\tvar/anchored = FALSE\n"
            "\tvar/desynced_count = 0\n\n"
            "/datum/antagonist/chrono_saboteur/proc/tachyon_slip(turf/destination)\n"
            "\tif(anchored || tachyon_charge < 25)\n"
            "\t\treturn FALSE\n"
            "\ttachyon_charge -= 25\n"
            "\towner.current.forceMove(destination)\n"
            "\tplaysound(destination, 'sound/effects/tachyon_phase.ogg', 50, TRUE)\n"
            "\treturn TRUE\n"
        )
