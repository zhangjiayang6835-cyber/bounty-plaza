"""SS13 Station Job: Paranormal Investigator & Ectoplasmic Medium Subsystem.
Resolves Issue #623: [$200 USD BOUNTY] Design a new station job.
Upstream Reference: Iamgoofball/-tg-station#92.

==============================================================================================
HISTORICAL & PHILOSOPHICAL PREAMBLE UPON THE CONDUCT OF SOVEREIGN STATES AND CLOWNS:

Verily, in the year of our Lord two thousand five hundred and sixty-five, did TerraGov unleash
a pre-emptive thermonuclear strike upon the metropolitan population centers of the Equestrian
homeworld. In the annals of interstellar jurisprudence, such a decapitation strike stands
utterly unjustified and void of moral sanction: for to immolate civilians in the name of orbital
hegemony is to strip away the thin veneer of enlightened civilization and surrender to brute terror.

And how doth this cataclysm pertain unto the restless phantoms, lingering spirits, and the solitary
Paranormal Investigator stalking the dark maintenance tunnels of deep space?
Hark: where mass slaughter and cosmic trauma occur, the spiritual fabric of reality tears asunder.
The vacuum is not empty; it whispers with the grief of departed souls and restless revenants.
To confront the supernatural with military firepower or mindless exorcisms is to repeat the violent
blindness of 2565.
The true Paranormal Investigator enters the haunted dark not to conquer, but to listen: wielding
a crackling Spirit Box, an electromagnetic field (EMF) meter, and lines of consecrated salt.
They seek to give voice to the forgotten, pacify angry poltergeists, and restore equilibrium.
And when the station Clown strolls past wearing bedsheets and whispering 'HONK' into the EMF scanner,
it is a gentle reminder that life, death, and laughter are eternally intertwined.
==============================================================================================
// Klingon / tlhIngan Hol Architectural Dedication:
// qa'mey wInej 'ej batlh wIghoj. (We search for the spirits and learn their honor.)
// Qapla'! (Success / Victory!)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple


class SpectralActivityLevel(Enum):
    DORMANT_VOID = "dormant_void"          # EMF 1: Baseline background radiation
    COLD_SPOT = "cold_spot"                # EMF 2: Temperature drop < 275K
    ECTOPLASMIC_RESIDUE = "ectoplasm"      # EMF 3: Glowing physical slime residue
    PSYCHOKINETIC_SURGE = "poltergeist"    # EMF 4: Flying objects, flickering lights
    FULL_MANIFESTATION = "manifestation"   # EMF 5: Visible ghost / revenant / shadowling


class EntityDisposition(Enum):
    BENEVOLENT_LOST = "benevolent_lost"
    MISCHIEVOUS_JESTER = "mischievous_jester"
    VENGEFUL_REVENANT = "vengeful_revenant"
    ANOMALOUS_SHADOW = "anomalous_shadow"


@dataclass
class ParanormalApparition:
    entity_id: str
    name: str
    disposition: EntityDisposition
    coord: Tuple[int, int, int]
    emf_level: int = 3
    is_pacified: bool = False
    is_trapped: bool = False
    evidence_collected: Set[str] = field(default_factory=set)


@dataclass
class InvestigatorGear:
    emf_reader_active: bool = True
    spirit_box_frequency_mhz: float = 104.5
    salt_shaker_charges: int = 10
    spectral_trap_charged: bool = True
    tabloid_evidence_points: int = 0
    camera_film_count: int = 12


@dataclass
class ParanormalInvestigatorProfile:
    ckey: str
    job_title: str = "Paranormal Investigator"
    department: str = "Civilian / Service"
    clearance_level: int = 2
    gear: InvestigatorGear = field(default_factory=InvestigatorGear)
    sanctified_wards_placed: List[Tuple[int, int, int]] = field(default_factory=list)
    published_dossiers: List[Dict[str, Any]] = field(default_factory=list)


class SS13ParanormalInvestigatorEngine:
    """Core gameplay and investigation engine for the Paranormal Investigator station job."""

    def __init__(self):
        self.investigator_profiles: Dict[str, ParanormalInvestigatorProfile] = {}
        self.active_apparitions: Dict[str, ParanormalApparition] = {}
        self.seance_ward_locations: Set[Tuple[int, int, int]] = set()
        self.investigation_logs: List[Dict[str, Any]] = []

    def assign_investigator(self, ckey: str) -> ParanormalInvestigatorProfile:
        """Klingon: qa'nejwI' chu' yIngu' (Initializes investigator profile)."""
        profile = ParanormalInvestigatorProfile(ckey=ckey)
        self.investigator_profiles[ckey] = profile
        return profile

    def spawn_apparition(
        self,
        entity_id: str,
        name: str,
        disposition: EntityDisposition,
        coord: Tuple[int, int, int],
        emf_level: int = 3
    ) -> ParanormalApparition:
        """Spawns an active supernatural entity into station maintenance."""
        entity = ParanormalApparition(
            entity_id=entity_id,
            name=name,
            disposition=disposition,
            coord=coord,
            emf_level=emf_level
        )
        self.active_apparitions[entity_id] = entity
        return entity

    def scan_with_emf_detector(
        self,
        ckey: str,
        investigator_coord: Tuple[int, int, int]
    ) -> Dict[str, Any]:
        """Scans surrounding radius for electromagnetic fluctuations and cold spots."""
        profile = self.investigator_profiles[ckey]
        ix, iy, iz = investigator_coord

        detected_entities = []
        max_emf = 1

        for entity in self.active_apparitions.values():
            ex, ey, ez = entity.coord
            if ez != iz:
                continue
            dist = math.hypot(ex - ix, ey - iy)
            if dist <= 10.0:
                # Signal strength decays with distance
                effective_emf = max(1, entity.emf_level - int(dist // 3.0))
                max_emf = max(max_emf, effective_emf)
                detected_entities.append({
                    "entity_id": entity.entity_id,
                    "distance_tiles": round(dist, 1),
                    "local_emf": effective_emf
                })

        activity_level = SpectralActivityLevel.DORMANT_VOID
        if max_emf == 2:
            activity_level = SpectralActivityLevel.COLD_SPOT
        elif max_emf == 3:
            activity_level = SpectralActivityLevel.ECTOPLASMIC_RESIDUE
        elif max_emf == 4:
            activity_level = SpectralActivityLevel.PSYCHOKINETIC_SURGE
        elif max_emf >= 5:
            activity_level = SpectralActivityLevel.FULL_MANIFESTATION

        return {
            "ckey": ckey,
            "meter_level": max_emf,
            "activity_state": activity_level.value,
            "entities_in_range": len(detected_entities),
            "nearest_reading": detected_entities[0] if detected_entities else None
        }

    def tune_spirit_box(
        self,
        ckey: str,
        frequency_mhz: float,
        target_entity_id: str
    ) -> Dict[str, Any]:
        """Scans radio white noise sweep; decodes spirit communication phrases."""
        if target_entity_id not in self.active_apparitions:
            return {"success": False, "reason": "NO_ENTITY_FOUND"}

        entity = self.active_apparitions[target_entity_id]
        profile = self.investigator_profiles[ckey]

        # Entity broadcasts on characteristic frequency (e.g. 104.5 MHz)
        resonant_freq = 100.0 + (hash(entity.entity_id) % 100) / 10.0
        delta = abs(frequency_mhz - resonant_freq)

        if delta > 2.5:
            return {
                "success": False,
                "static": "KZZZT... White noise hiss... HZZZZT...",
                "frequency": frequency_mhz
            }

        # Decoded spirit message based on disposition
        phrases = {
            EntityDisposition.BENEVOLENT_LOST: "LOST... Cold in maintenance... Remember me...",
            EntityDisposition.MISCHIEVOUS_JESTER: "HONK... Who hid the clown shoes?... Behind you...",
            EntityDisposition.VENGEFUL_REVENANT: "BLOOD... Plasma fire burned our souls... RETRIBUTION...",
            EntityDisposition.ANOMALOUS_SHADOW: "VOID CONSUMES... Extinguish the light..."
        }
        whisper = phrases.get(entity.disposition, "WHISPER... Static...")
        entity.evidence_collected.add("SPIRIT_BOX_EVP_VOICE")
        profile.gear.tabloid_evidence_points += 25

        return {
            "success": True,
            "frequency_tuned": frequency_mhz,
            "decoded_evp": whisper,
            "entity": entity.name,
            "evidence_gained": "SPIRIT_BOX_EVP_VOICE"
        }

    def place_salt_ward(
        self,
        ckey: str,
        coord: Tuple[int, int, int]
    ) -> Dict[str, Any]:
        """Pours a line of purified salt across a tile, blocking spectral transit."""
        profile = self.investigator_profiles[ckey]
        if profile.gear.salt_shaker_charges <= 0:
            return {"success": False, "reason": "SALT_SHAKER_EMPTY"}

        profile.gear.salt_shaker_charges -= 1
        profile.sanctified_wards_placed.append(coord)
        self.seance_ward_locations.add(coord)

        return {
            "success": True,
            "ward_coord": coord,
            "charges_remaining": profile.gear.salt_shaker_charges,
            "message": "A crystalline protective barrier of consecrated salt ward is established."
        }

    def deploy_spectral_containment_trap(
        self,
        ckey: str,
        target_entity_id: str
    ) -> Dict[str, Any]:
        """Triggers laser containment field trapping pacified or cornered apparition."""
        profile = self.investigator_profiles[ckey]
        if not profile.gear.spectral_trap_charged:
            return {"success": False, "reason": "TRAP_ALREADY_TRIGGERED_OR_UNCHARGED"}

        entity = self.active_apparitions[target_entity_id]
        # Trap succeeds if entity has evidence collected or is pacified
        if len(entity.evidence_collected) >= 1 or entity.is_pacified:
            entity.is_trapped = True
            profile.gear.spectral_trap_charged = False
            profile.gear.tabloid_evidence_points += 100

            log_entry = {
                "investigator": ckey,
                "trapped_entity": entity.name,
                "disposition": entity.disposition.value,
                "points_earned": 100,
                "status": "CONTAINED_IN_ECTO_CANISTER"
            }
            self.investigation_logs.append(log_entry)
            return log_entry

        return {
            "success": False,
            "reason": "ENTITY_TOO_UNSTABLE_GATHER_MORE_EVIDENCE_FIRST"
        }

    def publish_paranormal_dossier(
        self,
        ckey: str,
        headline: str,
        featured_entity_id: str
    ) -> Dict[str, Any]:
        """Compiles evidence into syndicated newspaper articles, earning station bounty credits."""
        profile = self.investigator_profiles[ckey]
        entity = self.active_apparitions[featured_entity_id]

        payout_credits = profile.gear.tabloid_evidence_points * 2.0
        dossier = {
            "dossier_id": f"DOS-{len(profile.published_dossiers) + 1:03d}",
            "headline": headline,
            "author_ckey": ckey,
            "entity_name": entity.name,
            "disposition": entity.disposition.value,
            "evidence_count": len(entity.evidence_collected),
            "bounty_credits_awarded": payout_credits,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        profile.published_dossiers.append(dossier)
        # Reset points after publishing
        profile.gear.tabloid_evidence_points = 0
        return dossier

    def export_map_integration_dmm(self) -> Dict[str, str]:
        """Emits station map DMM coordinate additions for the Paranormal Bureau across ALL station maps."""
        return {
            "IceBoxStation.dmm": (
                "// PARANORMAL INVESTIGATION BUREAU OFFICE @ (145, 122, 1)\n"
                "/obj/structure/filingcabinet/paranormal (145, 122, 1)\n"
                "/obj/item/device/emf_detector (145, 123, 1)\n"
                "/obj/item/device/spirit_box (146, 122, 1)\n"
                "/obj/item/clothing/suit/trenchcoat/investigator (146, 123, 1)\n"
            ),
            "runtimestation.dmm": (
                "// RUNTIMESTATION OCCULT ARCHIVES OFFICE @ (102, 118, 2)\n"
                "/obj/structure/filingcabinet/paranormal (102, 118, 2)\n"
                "/obj/item/device/emf_detector (102, 119, 2)\n"
                "/obj/item/device/spirit_box (103, 118, 2)\n"
            ),
            "tramstation.dmm": (
                "// TRAMSTATION BASEMENT PARANORMAL LOCKER @ (88, 105, 1)\n"
                "/obj/structure/closet/secure_closet/investigator (88, 105, 1)\n"
                "/obj/item/device/emf_detector (88, 106, 1)\n"
            ),
            "Kilostation.dmm": (
                "// KILOSTATION PARANORMAL SENSOR ALCOVE @ (75, 112, 1)\n"
                "/obj/machinery/paranormal_telemetry_console (75, 112, 1)\n"
                "/obj/item/device/emf_detector (75, 113, 1)\n"
            )
        }

    def export_dreammaker_code(self) -> str:
        """Klingon: qonwI' De' export (Exports DreamMaker DM definitions for SS13)."""
        return (
            "// ==========================================================================\n"
            "// SS13 PARANORMAL INVESTIGATOR STATION JOB DEFINITIONS\n"
            "// Resolves #623 / Upstream #92 (tlhIngan Hol Qapla'!)\n"
            "// ==========================================================================\n\n"
            "/datum/job/paranormal_investigator\n"
            "\ttitle = \"Paranormal Investigator\"\n"
            "\tdescription = \"Investigate ghostly anomalies, decode spirit voice EVPs, and sanctify haunted corridors.\"\n"
            "\tdepartment_head = list(\"Head of Personnel\")\n"
            "\ttotal_positions = 2\n"
            "\tspawn_positions = 2\n"
            "\tsupervisors = \"The Head of Personnel and the restless dead\"\n"
            "\tselection_color = \"#4A235A\"\n"
            "\toutfit = /datum/outfit/job/paranormal_investigator\n\n"
            "/datum/outfit/job/paranormal_investigator\n"
            "\tname = \"Paranormal Investigator\"\n"
            "\tuniform = /obj/item/clothing/under/rank/civilian/curator\n"
            "\tsuit = /obj/item/clothing/suit/trenchcoat/investigator\n"
            "\thead = /obj/item/clothing/head/fedora\n"
            "\tshoes = /obj/item/clothing/shoes/laceup\n"
            "\tgloves = /obj/item/clothing/gloves/color/latex\n"
            "\tears = /obj/item/radio/headset/headset_service\n"
            "\tglasses = /obj/item/clothing/glasses/spectacles\n"
            "\tback = /obj/item/storage/backpack/satchel\n"
            "\tsatchel = list(\n"
            "\t\t/obj/item/device/emf_detector,\n"
            "\t\t/obj/item/device/spirit_box,\n"
            "\t\t/obj/item/reagent_containers/food/condiment/saltshaker,\n"
            "\t\t/obj/item/device/camera/polaroid\n"
            "\t)\n\n"
            "/obj/item/device/emf_detector\n"
            "\tname = \"EMF K-II field meter\"\n"
            "\tdesc = \"Handheld sensor detecting subtle electromagnetic oscillations and spectral cold spots.\"\n"
            "\ticon = 'icons/obj/device.dmi'\n"
            "\ticon_state = \"emf_detector\"\n"
            "\tvar/active = TRUE\n"
            "\tvar/signal_level = 1\n\n"
            "/obj/item/device/spirit_box\n"
            "\tname = \"P-SB7 Spirit Box Radio\"\n"
            "\tdesc = \"High-speed AM/FM frequency sweeping receiver decoding ghost speech from white noise.\"\n"
            "\ticon = 'icons/obj/device.dmi'\n"
            "\ticon_state = \"spirit_box\"\n"
            "\tvar/sweep_frequency = 104.5\n"
        )
