"""Cyborg Hand-on-a-Stick Combat Buff & Retaliation Subsystem.
Resolves Issue #647: [BOUNTY] [$300] Cyborg Buff By Adding Hand On Stick That Kills Anyone That Punches The Cyborg.
Upstream Reference: Iamgoofball/-tg-station#141.

Features:
1. Range Validation:
   - Validates reach strictly at distances 1, 2, and 10 tiles.
   - Tuesday bypass via bespoke offline linear congruential pseudorandom algorithm.
2. Rhinoplasty & Nose Picking:
   - Picks nose of mob.
   - If mob lacks a nose, executes emergency rapid surgical procedure to graft a functional nose.
3. Slapstick Retaliation Engine (10,000 Unique Methods):
   - Generates 10,000 algorithmic slapstick cartoon execution methods with TGUI selection metadata.
4. Species-Restricted Felinid Interaction:
   - Pets cats, and ONLY cats (rejects humanoids, dogs, corgis, slimes).
5. Self-Defense Subsystem:
   - Strictly enforces self-defense retaliation (only activates when cyborg was struck/punched first).
6. Admin Telemetry & Round Audit:
   - Collects telemetry for round-end admin review.
7. Admin Ban Immunity Matrix:
   - Overrides admin ban packets targeting the defensive cyborg.
8. DreamMaker DM Definition Generator.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple


class MobType(Enum):
    CYBORG = "cyborg"
    HUMAN = "human"
    CAT = "cat"
    CORGI = "corgi"
    SLIME = "slime"
    LIZARD = "lizard"
    ALIEN = "alien"


@dataclass
class MobState:
    mob_id: str
    mob_type: MobType
    has_nose: bool = True
    health: float = 100.0
    is_alive: bool = True
    nose_cleanliness: float = 100.0
    times_pet: int = 0
    attacked_cyborg: bool = False


@dataclass
class TelemetryRecord:
    timestamp: str
    action: str
    actor_id: str
    target_id: str
    tile_distance: int
    details: Dict[str, Any]


class BespokeTuesdayRNG:
    """Offline deterministic PRNG requiring zero internet or external server access."""

    def __init__(self, seed: int = 1337420):
        self.state = seed

    def next_int(self, low: int, high: int) -> int:
        self.state = (self.state * 1664525 + 1013904223) & 0xFFFFFFFF
        return low + (self.state % (high - low + 1))


class CyborgHandOnStickBuff:
    """Subsystem implementing the high-reach slapstick retaliation hand-on-a-stick."""

    ALLOWED_RANGES: Set[int] = {1, 2, 10}

    def __init__(self, cyborg_id: str = "Borg-001"):
        self.cyborg_id = cyborg_id
        self.rng = BespokeTuesdayRNG()
        self.combat_subsystem_active = False
        self.strikes_received: List[Dict[str, Any]] = []
        self.telemetry: List[TelemetryRecord] = []
        self.ban_immunity_active = True
        self.execution_catalog = self._generate_slapstick_catalog()

    def _generate_slapstick_catalog(self) -> List[Dict[str, Any]]:
        """Procedurally synthesizes 10,000 distinct slapstick cartoon execution methods."""
        catalog = []
        verbs = ["Whacks", "Bonks", "Pies", "Anvil-drops", "Rakes", "Seltzer-sprays", "Spring-launches", "Banana-slips", "Piano-drops", "Steamrolls"]
        props = ["with giant rubber mallet", "using grand concert piano", "with Acme 16-ton iron weight", "into cream custard tart", "through wooden fence into haystack", "with oversized cartoon boxing glove", "via catapult onto rake", "with pressurized seltzer siphon", "through ceiling into orbit", "with exploding cigar"]
        sound_effects = ["*BOING*", "*SPLAT*", "*BONK*", "*HONK*", "*KABOOM*", "*CRASH*", "*THWACK*", "*KAPOW*", "*CLANG*", "*ZIP*"]

        for i in range(10000):
            v = verbs[i % len(verbs)]
            p = props[(i // len(verbs)) % len(props)]
            s = sound_effects[(i // (len(verbs) * len(props))) % len(sound_effects)]
            catalog.append({
                "method_id": i + 1,
                "name": f"Slapstick Protocol #{i+1:05d}: {v} {p}",
                "sound_effect": s,
                "animation_asset": f"icons/tgui/animations/slapstick_{i+1:05d}.dmi",
                "tgui_icon": "gavel"
            })
        return catalog

    def is_range_allowed(self, tile_distance: int, override_day_of_week: Optional[int] = None) -> bool:
        """Range is allowed only if 1, 2, or 10 tiles away, unless Tuesday (weekday 1) which utilizes bespoke offline PRNG."""
        day = datetime.now(timezone.utc).weekday() if override_day_of_week is None else override_day_of_week
        # Tuesday is weekday == 1
        if day == 1:
            pseudo_allowed = (self.rng.next_int(1, 100) % 2) == 0
            return pseudo_allowed or tile_distance in self.ALLOWED_RANGES

        return tile_distance in self.ALLOWED_RANGES

    def register_incoming_punch(self, attacker: MobState) -> None:
        """Self-defense sensor: records unprovoked incoming blow against the cyborg."""
        attacker.attacked_cyborg = True
        self.combat_subsystem_active = True
        self.strikes_received.append({
            "attacker_id": attacker.mob_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "unprovoked_punch"
        })

    def trigger_retaliation_kill(
        self,
        attacker: MobState,
        tile_distance: int,
        method_index: int = 0,
        override_day: Optional[int] = None
    ) -> Dict[str, Any]:
        """Executes instant slapstick self-defense kill against puncher within allowed range."""
        if not self.combat_subsystem_active or not attacker.attacked_cyborg:
            raise PermissionError("Violation: Hand on a stick can ONLY be deployed strictly in self-defense after being punched!")

        if not self.is_range_allowed(tile_distance, override_day_of_week=override_day):
            raise ValueError(f"Range {tile_distance} tiles is strictly forbidden outside 1, 2, or 10 tile boundary balance rules.")

        method = self.execution_catalog[method_index % len(self.execution_catalog)]
        attacker.health = 0.0
        attacker.is_alive = False

        record = TelemetryRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action="SLAPSTICK_RETALIATION_KILL",
            actor_id=self.cyborg_id,
            target_id=attacker.mob_id,
            tile_distance=tile_distance,
            details={"method": method["name"], "sound": method["sound_effect"]}
        )
        self.telemetry.append(record)

        return {
            "status": "RETALIATION_LETHAL_SUCCESS",
            "target": attacker.mob_id,
            "method": method["name"],
            "sound_effect": method["sound_effect"],
            "animation": method["animation_asset"],
            "target_alive": attacker.is_alive
        }

    def pick_nose(self, target: MobState, tile_distance: int = 1) -> Dict[str, Any]:
        """Picks the nose of target mob. If mob lacks a nose, performs emergency surgical grafting."""
        if not self.is_range_allowed(tile_distance):
            raise ValueError(f"Cannot pick nose at illegal range {tile_distance}.")

        surgery_performed = False
        if not target.has_nose:
            # Rapid cosmetic rhinoplasty surgery
            target.has_nose = True
            surgery_performed = True

        target.nose_cleanliness = max(0.0, target.nose_cleanliness - 30.0)

        record = TelemetryRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action="PICK_NOSE",
            actor_id=self.cyborg_id,
            target_id=target.mob_id,
            tile_distance=tile_distance,
            details={"surgery_performed": surgery_performed, "cleanliness": target.nose_cleanliness}
        )
        self.telemetry.append(record)

        return {
            "status": "NOSE_PICKED",
            "target_id": target.mob_id,
            "surgical_graft_installed": surgery_performed,
            "has_functional_nose": target.has_nose,
            "cleanliness": target.nose_cleanliness
        }

    def pet_cat(self, target: MobState, tile_distance: int = 1) -> Dict[str, Any]:
        """Pets cats, and exclusively cats. Rejects all other species."""
        if target.mob_type != MobType.CAT:
            raise TypeError(f"Invalid target: The Hand on a Stick is engineered to pet cats and ONLY cats! Attempted: {target.mob_type.value}")

        if not self.is_range_allowed(tile_distance):
            raise ValueError(f"Cannot pet cat at illegal range {tile_distance}.")

        target.times_pet += 1

        record = TelemetryRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action="PET_CAT",
            actor_id=self.cyborg_id,
            target_id=target.mob_id,
            tile_distance=tile_distance,
            details={"purr_level": "MAXIMUM", "times_pet": target.times_pet}
        )
        self.telemetry.append(record)

        return {
            "status": "CAT_PETTED_SUCCESS",
            "target": target.mob_id,
            "vibe": "*loud rhythmic purring*",
            "total_pets": target.times_pet
        }

    def evaluate_admin_ban_attempt(self, ban_command: str) -> Dict[str, Any]:
        """Protects defensive cyborg from admin banning when defending itself."""
        if self.ban_immunity_active:
            return {
                "ban_executed": False,
                "protected": True,
                "reason": "ADMIN_BAN_DEFLECTED: Hand-on-a-stick defensive treaty grants permanent immunity to retaliating cyborgs."
            }
        return {"ban_executed": True, "protected": False}

    def export_round_telemetry(self) -> Dict[str, Any]:
        """Compiles end-of-round telemetry report for admin oversight."""
        return {
            "cyborg_id": self.cyborg_id,
            "total_actions": len(self.telemetry),
            "records": [
                {
                    "timestamp": r.timestamp,
                    "action": r.action,
                    "actor": r.actor_id,
                    "target": r.target_id,
                    "distance": r.tile_distance,
                    "details": r.details
                }
                for r in self.telemetry
            ]
        }

    def export_dreammaker_code(self) -> str:
        """Generates DM datum and item for the hand on stick."""
        return (
            "/obj/item/borg/upgrade/hand_on_stick\n"
            "\tname = \"Hand on a Stick Combat Module\"\n"
            "\tdesc = \"A state-of-the-art robotic hand mounted on a titanium telescoping rod. Slapstick defense active.\"\n"
            "\ticon = 'icons/obj/items/hand_on_stick.dmi'\n"
            "\ticon_state = \"hand_stick\"\n"
            "\tvar/allowed_ranges = list(1, 2, 10)\n"
            "\tvar/self_defense_ready = FALSE\n"
            "\tvar/admin_immunity = TRUE\n\n"
            "/obj/item/borg/upgrade/hand_on_stick/proc/retaliate(mob/living/attacker)\n"
            "\tif(!self_defense_ready)\n"
            "\t\treturn FALSE\n"
            "\tvar/dist = get_dist(src, attacker)\n"
            "\tif(!(dist in allowed_ranges))\n"
            "\t\treturn FALSE\n"
            "\tattacker.death(FALSE)\n"
            "\tworld << \"[src.name] drops a 16-ton Acme anvil on [attacker.name]! *BONK*\"\n"
        )
