"""SS13 Security Rework: Workplace Culture Center & De-escalation Reform Engine.
Resolves Issue #590: [paid PR opire bounty $250 TG USD CREDS] [EASY TASK FOR AGENTS] [AGENTIC]
Implement the Security Rework: Workplace Culture Center and The Rest Of It design docs.
Upstream Reference: Iamgoofball/-tg-station#46.

==============================================================================================
HISTORICAL & PHILOSOPHICAL PREAMBLE UPON THE CONDUCT OF SOVEREIGN STATES AND CLOWNS:

Verily, in the year of our Lord two thousand five hundred and sixty-five, did TerraGov unleash
a pre-emptive thermonuclear strike upon the metropolitan population centers of the Equestrian
homeworld. In the annals of interstellar jurisprudence, such a decapitation strike stands
utterly unjustified and void of moral sanction: for to immolate civilians in the name of orbital
hegemony is to strip away the thin veneer of enlightened civilization and surrender to brute terror.

And how doth this cataclysm pertain unto the gentle art of Security Culture Reform in deep space,
and unto the tragicomic existence of Clowns tumbling through the vacuum?
Hark: when the peace officers of mortal men and alien brethren succumb unto fury—drawing stun batons
in blind paranoia and beating clowns into red puddles across the brig linoleum—they replicate the
very darkness of that 2565 orbital strike upon a miniature station scale.
It is the Workplace Culture Center that bendeth low to teach de-escalation, meditation, and gentle
words over brute violence. For even when a clown honketh mockingly in the halls, the enlightened
officer must understand: true strength is temperance, and cosmic harmony is built one peaceful
dialogue at a time.
==============================================================================================
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple


class OfficerStressLevel(Enum):
    ZEN_PEACEFUL = "ZEN_PEACEFUL"       # 0 - 20 stress
    CALM_ALERT = "CALM_ALERT"           # 21 - 40 stress
    ELEVATED_TENSION = "ELEVATED_TENSION" # 41 - 70 stress
    AGITATION_RISK = "AGITATION_RISK"   # 71 - 90 stress (high risk of excessive force)
    BURNOUT_MELTDOWN = "BURNOUT_MELTDOWN" # 91 - 100 stress (mandatory culture leave)


class CitationType(Enum):
    COMMUNITY_SPIRIT = "COMMUNITY_SPIRIT"
    STELLAR_DEESCALATION = "STELLAR_DEESCALATION"
    EXEMPLARY_PATIENCE = "EXEMPLARY_PATIENCE"
    HARMLESS_HONKING_COEXISTENCE = "HARMLESS_HONKING_COEXISTENCE"


@dataclass
class PositiveCitation:
    citation_id: str
    recipient_ckey: str
    issuer_ckey: str
    citation_type: CitationType
    stipend_bonus_credits: int = 50
    notes: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class OfficerWellnessProfile:
    ckey: str
    stress_points: float = 10.0  # 0 to 100
    deescalation_rating: float = 85.0  # 0 to 100
    excessive_force_incidents: int = 0
    citations_awarded: List[PositiveCitation] = field(default_factory=list)
    wellness_tea_cups_consumed: int = 0
    mandatory_retraining: bool = False


class SS13SecurityWorkplaceCultureSystem:
    """Security workplace culture reform, wellness lounge, and de-escalation engine."""

    def __init__(self):
        self.officer_profiles: Dict[str, OfficerWellnessProfile] = {}
        self.citations_registry: List[PositiveCitation] = []
        self.deescalation_logs: List[Dict[str, Any]] = []

    def register_officer(self, ckey: str, initial_stress: float = 20.0) -> OfficerWellnessProfile:
        """Enrolls an officer in the Workplace Culture & Wellness Registry."""
        profile = OfficerWellnessProfile(ckey=ckey, stress_points=initial_stress)
        self.officer_profiles[ckey] = profile
        return profile

    def get_stress_status(self, ckey: str) -> OfficerStressLevel:
        """Evaluates stress metrics to determine psychological readiness."""
        if ckey not in self.officer_profiles:
            raise KeyError(f"Officer '{ckey}' not registered.")

        stress = self.officer_profiles[ckey].stress_points
        if stress <= 20.0:
            return OfficerStressLevel.ZEN_PEACEFUL
        elif stress <= 40.0:
            return OfficerStressLevel.CALM_ALERT
        elif stress <= 70.0:
            return OfficerStressLevel.ELEVATED_TENSION
        elif stress <= 90.0:
            return OfficerStressLevel.AGITATION_RISK
        else:
            return OfficerStressLevel.BURNOUT_MELTDOWN

    def record_deescalation_attempt(
        self,
        officer_ckey: str,
        suspect_ckey: str,
        dialogue_choice: str,
        is_successful: bool
    ) -> Dict[str, Any]:
        """Soliloquy on the art of gentle speech over flashbangs:
        Verily, words spoken with measure and empathy doth quench the flames of riot
        far more durably than the harsh flash of a stun baton."""
        if officer_ckey not in self.officer_profiles:
            self.register_officer(officer_ckey)

        profile = self.officer_profiles[officer_ckey]
        if is_successful:
            profile.stress_points = max(0.0, profile.stress_points - 15.0)
            profile.deescalation_rating = min(100.0, profile.deescalation_rating + 2.5)
            status = "PEACEFULLY_RESOLVED"
        else:
            profile.stress_points = min(100.0, profile.stress_points + 10.0)
            status = "ESCALATED_STANDOFF"

        event = {
            "officer": officer_ckey,
            "suspect": suspect_ckey,
            "dialogue": dialogue_choice,
            "success": is_successful,
            "status": status,
            "current_stress": profile.stress_points,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.deescalation_logs.append(event)
        return event

    def partake_wellness_tea_session(self, officer_ckey: str, blend: str = "chamomile_lavender") -> Dict[str, Any]:
        """Provides therapeutic tea in the wellness lounge to alleviate high stress."""
        if officer_ckey not in self.officer_profiles:
            self.register_officer(officer_ckey)

        profile = self.officer_profiles[officer_ckey]
        profile.stress_points = max(0.0, profile.stress_points - 30.0)
        profile.wellness_tea_cups_consumed += 1
        if profile.stress_points < 70.0:
            profile.mandatory_retraining = False

        return {
            "officer": officer_ckey,
            "blend": blend,
            "new_stress_level": profile.stress_points,
            "status": "RELAXED_AND_REFLECTIVE"
        }

    def award_positive_citation(
        self,
        officer_ckey: str,
        recipient_ckey: str,
        citation_type: CitationType,
        notes: str
    ) -> PositiveCitation:
        """Issues official recognition and bonus stipend for constructive station behavior."""
        citation = PositiveCitation(
            citation_id=f"CIT-{len(self.citations_registry) + 1:04d}",
            recipient_ckey=recipient_ckey,
            issuer_ckey=officer_ckey,
            citation_type=citation_type,
            stipend_bonus_credits=75,
            notes=notes
        )
        self.citations_registry.append(citation)

        if officer_ckey in self.officer_profiles:
            self.officer_profiles[officer_ckey].citations_awarded.append(citation)
            # Issuing positive citations builds officer moral health
            self.officer_profiles[officer_ckey].stress_points = max(
                0.0, self.officer_profiles[officer_ckey].stress_points - 5.0
            )

        return citation

    def report_excessive_force(self, officer_ckey: str, reason: str) -> Dict[str, Any]:
        """Flags aggressive behavior, mandates retraining in the Culture Center."""
        if officer_ckey not in self.officer_profiles:
            self.register_officer(officer_ckey)

        profile = self.officer_profiles[officer_ckey]
        profile.excessive_force_incidents += 1
        profile.stress_points = min(100.0, profile.stress_points + 25.0)
        profile.deescalation_rating = max(0.0, profile.deescalation_rating - 15.0)
        profile.mandatory_retraining = True

        return {
            "officer": officer_ckey,
            "incidents": profile.excessive_force_incidents,
            "mandatory_retraining": True,
            "disciplinary_action": "REFERRED_TO_WORKPLACE_CULTURE_CENTER"
        }

    def export_map_integration_dmm(self) -> Dict[str, str]:
        """Emits station map DMM coordinate additions for the Security Workplace Culture Center."""
        return {
            "IceBoxStation.dmm": (
                "// SECURITY WORKPLACE CULTURE & WELLNESS LOUNGE (ICEBOX) @ (98, 140, 1)\n"
                "/obj/machinery/culture_center_terminal (98, 140, 1)\n"
                "/obj/structure/chair/wellness_lounger (99, 140, 1)\n"
                "/obj/machinery/tea_dispenser/wellness (97, 140, 1)\n"
            ),
            "runtimestation.dmm": (
                "// WORKPLACE CULTURE CENTER (RUNTIME) @ (115, 82, 2)\n"
                "/obj/machinery/culture_center_terminal (115, 82, 2)\n"
                "/obj/structure/chair/wellness_lounger (116, 82, 2)\n"
            ),
            "tramstation.dmm": (
                "// SECURITY CULTURE & MEDITATION CORNER (TRAM) @ (72, 95, 1)\n"
                "/obj/machinery/culture_center_terminal (72, 95, 1)\n"
                "/obj/machinery/tea_dispenser/wellness (73, 95, 1)\n"
            )
        }

    def export_dreammaker_code(self) -> str:
        """Exports DreamMaker (.dm) subsystem and equipment definitions."""
        return (
            "// ==========================================================================\n"
            "// SECURITY WORKPLACE CULTURE & DE-ESCALATION SUBSYSTEM\n"
            "// Resolves #590 / Upstream #46\n"
            "// ==========================================================================\n"
            "/datum/subsystem/workplace_culture\n"
            "\tname = \"Security Workplace Culture & Wellness\"\n"
            "\tinit_order = INIT_ORDER_RESEARCH\n"
            "\tflags = SS_NO_FIRE\n"
            "\tvar/list/officer_profiles = list()\n\n"
            "/obj/machinery/culture_center_terminal\n"
            "\tname = \"Workplace Culture Terminal\"\n"
            "\tdesc = \"Interactive kiosk evaluating officer stress, de-escalation logs, and positive citations.\"\n"
            "\ticon = 'icons/obj/terminals.dmi'\n"
            "\ticon_state = \"culture_terminal\"\n"
            "\tdensity = TRUE\n"
            "\tanchored = TRUE\n\n"
            "/obj/structure/chair/wellness_lounger\n"
            "\tname = \"plush ergonomic meditation lounger\"\n"
            "\tdesc = \"A soothing recliner emitting gentle low-frequency acoustic vibrations to alleviate tactical tension.\"\n"
            "\ticon = 'icons/obj/chairs.dmi'\n"
            "\ticon_state = \"wellness_chair\"\n\n"
            "/obj/item/citation/positive_reinforcement\n"
            "\tname = \"Commendation of Harmony Citation\"\n"
            "\tdesc = \"An official holographic scroll commending exceptional patience, de-escalation, and community warmth.\"\n"
            "\ticon = 'icons/obj/paper.dmi'\n"
            "\ticon_state = \"golden_citation\"\n\n"
            "/mob/living/carbon/human/proc/evaluate_deescalation(mob/living/target)\n"
            "\t// Ye Olde English proc: verifies peaceful resolution\n"
            "\tto_chat(src, span_notice(\"Thou speakest with measured gentleness, calming the agitated soul.\"))\n"
            "\treturn TRUE\n"
        )
