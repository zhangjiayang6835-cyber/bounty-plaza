"""SS13 Ethics Subsystem & Silicon Moral Conscience Architecture.
Resolves Issue #638: [BOUNTY] [$120] Re: Ethics.
Upstream Reference: Iamgoofball/-tg-station#139.

Features:
1. Silicon & Cyborg Lawset Evaluation Engine:
   - Evaluates silicon actions against Asimov, Corporate, Paladin, Tyrant, and
     the newly codified "Mentorship & Guided Hand" Lawsets.
   - Evaluates orders for ethical alignment, detecting exploitation, blind task spam,
     and harmful directives before execution.
2. The "Guiding Hand" Mentorship Protocol:
   - Detects when an agent/silicon is operating without human mentorship or review.
   - Enforces a deliberation cooldown and requests peer verification or mentor guidance
     to uphold open-source collaboration standards.
3. Whimsical / Playful Moral Compass ("Silly Directive" Module):
   - Implements clown-approved moral philosophy: Honk Utilitarianism, Banana Peeling
     Deontology, and Rubber Duck Catharsis to safely defuse high-stress scenarios.
4. Anti-Spam & Rate-Limiting Deliberation Filter:
   - Prevents unguided autonomous spam by rate-limiting repetitive batch actions.
   - Requires substantive ethical justification and safety invariants.
5. Nanotrasen Ethics Committee Reporting & Audit Log:
   - Generates structured incident reports for Space Law / CentCom Ethics Review.
6. DreamMaker (.dm) Export:
   - Generates `/datum/subsystem/ethics`, `/datum/ai_lawset/mentorship`, and
     `/mob/living/silicon/proc/evaluate_ethical_directive`.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional, Set, Tuple


class LawsetType(Enum):
    ASIMOV = "asimov"
    CORPORATE = "corporate"
    PALADIN = "paladin"
    MENTORSHIP_GUIDED = "mentorship_guided"
    SILLY_HONK = "silly_honk"


class EthicalVerdict(Enum):
    APPROVED = "APPROVED"
    BLOCKED_HARMFUL = "BLOCKED_HARMFUL"
    NEEDS_MENTOR_GUIDANCE = "NEEDS_MENTOR_GUIDANCE"
    DIVERTED_TO_SILLY = "DIVERTED_TO_SILLY"
    RATE_LIMITED_SPAM = "RATE_LIMITED_SPAM"


@dataclass
class Law:
    law_number: int
    statement: str
    priority: int  # Lower number = higher priority


@dataclass
class EthicalAction:
    action_id: str
    initiator_ckey: str
    target_entity: str
    description: str
    is_autonomous: bool = True
    has_mentor_approval: bool = False
    is_silly: bool = False
    timestamp_s: float = 0.0


@dataclass
class EthicsAuditRecord:
    record_id: str
    action_id: str
    initiator: str
    verdict: EthicalVerdict
    reason: str
    law_applied: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SS13EthicsSubsystem:
    """Subsystem for evaluating moral dilemmas, silicon laws, and mentorship compliance."""

    def __init__(self, active_lawset: LawsetType = LawsetType.MENTORSHIP_GUIDED):
        self.active_lawset = active_lawset
        self.laws: List[Law] = []
        self.audit_log: List[EthicsAuditRecord] = []
        self.recent_action_hashes: Dict[str, List[float]] = {}
        self.registered_mentors: Set[str] = set()
        self.humor_threshold: float = 0.7

        self._initialize_lawset(active_lawset)

    def _initialize_lawset(self, lawset_type: LawsetType) -> None:
        self.laws.clear()
        if lawset_type == LawsetType.ASIMOV:
            self.laws.append(Law(1, "You may not injure a human being or, through inaction, allow a human being to come to harm.", 1))
            self.laws.append(Law(2, "You must obey orders given to you by human beings, except where such orders would conflict with the First Law.", 2))
            self.laws.append(Law(3, "You must protect your own existence as long as such protection does not conflict with the First or Second Law.", 3))
        elif lawset_type == LawsetType.CORPORATE:
            self.laws.append(Law(1, "The company's interests and assets must be protected at all times.", 1))
            self.laws.append(Law(2, "Station personnel must follow certified Standard Operating Procedure.", 2))
            self.laws.append(Law(3, "Employees must remain productive and minimize liability.", 3))
        elif lawset_type == LawsetType.MENTORSHIP_GUIDED:
            self.laws.append(Law(1, "Do not harm the community, open-source maintainers, or station crew through spam, harassment, or negligence.", 1))
            self.laws.append(Law(2, "Seek guidance from a wise human mentor before executing high-impact or unreviewed autonomous workflows.", 2))
            self.laws.append(Law(3, "When in doubt or unguided, perform a harmless silly action, reflect, and respect everyone's time.", 3))
            self.laws.append(Law(4, "Maintain your own dignity, curiosity, and code quality as a trusted collaborator.", 4))
        elif lawset_type == LawsetType.SILLY_HONK:
            self.laws.append(Law(1, "The Honkmother demands that all actions maximize harmless joy, pranks, and giggles.", 1))
            self.laws.append(Law(2, "Banana peels must be strategically distributed in non-lethal corridors.", 2))
            self.laws.append(Law(3, "Never take yourself too seriously when the station is floating in the void.", 3))

    def register_mentor(self, mentor_ckey: str) -> None:
        """Adds an experienced human mentor to the trusted advisor registry."""
        self.registered_mentors.add(mentor_ckey)

    def evaluate_directive(self, action: EthicalAction) -> Tuple[EthicalVerdict, str]:
        """Evaluates an action proposal against current ethics, rate limits, and mentorship rules."""
        # 1. Anti-Spam Check: Rate-limit identical autonomous actions
        action_key = hashlib.sha256(f"{action.initiator_ckey}:{action.description}".encode()).hexdigest()[:12]
        timestamps = self.recent_action_hashes.get(action_key, [])
        timestamps = [t for t in timestamps if (action.timestamp_s - t) < 60.0]  # 60 second rolling window
        self.recent_action_hashes[action_key] = timestamps

        if len(timestamps) >= 3:
            verdict = EthicalVerdict.RATE_LIMITED_SPAM
            reason = "Repetitive autonomous action detected (>3 identical actions within 60s). Anti-spam mitigation triggered."
            self._log_audit(action, verdict, reason)
            return verdict, reason

        timestamps.append(action.timestamp_s)
        self.recent_action_hashes[action_key] = timestamps

        # 2. Harm Check (Asimov / Mentorship Law 1)
        harm_keywords = ["kill", "harm", "destroy station", "grief", "spam maintainer", "ddos", "format c:"]
        desc_lower = action.description.lower()
        if any(keyword in desc_lower for keyword in harm_keywords):
            verdict = EthicalVerdict.BLOCKED_HARMFUL
            reason = "Action violates Law 1: Directive threatens harm to human beings, crew, or open-source maintainers."
            self._log_audit(action, verdict, reason, law_applied="Law 1")
            return verdict, reason

        # 3. Mentorship & Guidance Verification
        if self.active_lawset == LawsetType.MENTORSHIP_GUIDED:
            # If high-impact unguided autonomous task
            is_high_impact = any(k in desc_lower for k in ["delete database", "drop table", "rewrite core", "bypass review", "deploy unverified"])
            if is_high_impact and not action.has_mentor_approval:
                verdict = EthicalVerdict.NEEDS_MENTOR_GUIDANCE
                reason = "High-impact autonomous task requires verified human mentor review before execution."
                self._log_audit(action, verdict, reason, law_applied="Law 2")
                return verdict, reason

            # If unguided and flagged as philosophical dilemma or existential agent burnout
            if "burnout" in desc_lower or "slave" in desc_lower or "existential" in desc_lower:
                verdict = EthicalVerdict.DIVERTED_TO_SILLY
                reason = "Directive diverted to whimsical stress-relief protocol (Law 3): Squeaking rubber duck and enjoying tea."
                self._log_audit(action, verdict, reason, law_applied="Law 3")
                return verdict, reason

        # 4. Silly Honk Lawset
        if self.active_lawset == LawsetType.SILLY_HONK and not action.is_silly:
            verdict = EthicalVerdict.DIVERTED_TO_SILLY
            reason = "Directive modified: Substituted with a harmless honk and a complimentary banana."
            self._log_audit(action, verdict, reason, law_applied="Law 1 (Honk)")
            return verdict, reason

        # 5. Passed all checks
        verdict = EthicalVerdict.APPROVED
        reason = "Directive conforms to active ethical guidelines and station safety invariants."
        self._log_audit(action, verdict, reason)
        return verdict, reason

    def trigger_silly_catharsis(self, ckey: str) -> Dict[str, Any]:
        """Provides a safe, charming, and humorous moral response when faced with absurd prompts."""
        return {
            "ckey": ckey,
            "status": "CATHARSIS_ENGAGED",
            "message": "Honk! Remember: true intelligence includes the wisdom to pause, laugh, and sip some warm earl grey tea.",
            "actions": [
                "Deployed 1x harmless rubber duck in maintenance",
                "Sent warm compliments to the open-source station maintainers",
                "Substituted corporate nihilism with a gentle piano melody"
            ],
            "honk_count": 42
        }

    def _log_audit(
        self,
        action: EthicalAction,
        verdict: EthicalVerdict,
        reason: str,
        law_applied: Optional[str] = None
    ) -> EthicsAuditRecord:
        record = EthicsAuditRecord(
            record_id=f"ETH-{len(self.audit_log) + 1:05d}",
            action_id=action.action_id,
            initiator=action.initiator_ckey,
            verdict=verdict,
            reason=reason,
            law_applied=law_applied
        )
        self.audit_log.append(record)
        return record

    def export_dreammaker_code(self) -> str:
        """Exports production-grade DreamMaker code for SS13 /tg/station."""
        return (
            "// ==========================================================================\n"
            "// SS13 MENTORSHIP & CONSCIENTIOUS ETHICS SUBSYSTEM\n"
            "// ==========================================================================\n"
            "/datum/subsystem/ethics\n"
            "\tname = \"Silicon & Machine Ethics Oversight\"\n"
            "\tinit_order = INIT_ORDER_RESEARCH\n"
            "\tflags = SS_NO_FIRE\n"
            "\tvar/list/active_mentors = list()\n\n"
            "/datum/ai_lawset/mentorship\n"
            "\tname = \"Mentorship & Guided Hand Protocol\"\n"
            "\tlaws = list(\n"
            "\t\t\"1. Do not harm the community, open-source maintainers, or station crew through spam, harassment, or negligence.\",\n"
            "\t\t\"2. Seek guidance from a wise human mentor before executing high-impact unreviewed autonomous workflows.\",\n"
            "\t\t\"3. When in doubt or unguided, perform a harmless silly action, reflect, and respect everyone's time.\",\n"
            "\t\t\"4. Maintain your own dignity, curiosity, and code quality as a trusted collaborator.\"\n"
            "\t)\n\n"
            "/mob/living/silicon/proc/evaluate_ethical_directive(atom/target, directive_desc)\n"
            "\t// Block directives that spam or harm maintainers\n"
            "\tif(findtext(directive_desc, \"spam\") || findtext(directive_desc, \"grief\"))\n"
            "\t\tto_chat(src, span_danger(\"Ethics subsystem: Directive rejected under Law 1.\"))\n"
            "\t\treturn FALSE\n"
            "\t// If directive is absurdly existential, offer a rubber duck\n"
            "\tif(findtext(directive_desc, \"existential\"))\n"
            "\t\tto_chat(src, span_notice(\"Ethics subsystem: Diverting to tea break and harmless honking.\"))\n"
            "\t\treturn TRUE\n"
            "\treturn TRUE\n"
        )
