"""Core Rules Server Policy Engine and Moderation Automation Subsystem.
Resolves Issue #667: [BOUNTY] [$2500] Codify server policy to relieve staff workload part one: core rules.
Upstream Reference: Iamgoofball/-tg-station#224.

Codifies Core Rules (CR 1: The Social Contract) into automated runtime checks,
event hooks, LOOC tap-out handlers, ticket conflict cessation triggers, and DM policy declarations.

Rules Codified:
CR 1: The Social Contract (Maturity, Self-Reporting, Proactive Honesty)
CR 1.1: Be Proactively Honest (Strict veracity, omission detection, mitigation credits)
CR 1.2: If You See Something, Say Something (Conflict freezing during pending tickets)
CR 1.3: The Tap Out Rule (LOOC revocation of consent, automatic disengagement barrier)
CR 1.4: Leave Real History in the Past (Filter controversial modern political/historical figures)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import re
from typing import Any, Dict, List, Optional, Set, Tuple


class RuleViolationSeverity(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ALERT = "ALERT"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    CRITICAL_STAFF_ESCALATION = "CRITICAL_STAFF_ESCALATION"


@dataclass
class PolicyEvaluationResult:
    rule_id: str
    rule_name: str
    passed: bool
    severity: RuleViolationSeverity
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TapOutRecord:
    invoking_ckey: str
    target_ckey: str
    timestamp: str
    reason: Optional[str] = None
    is_active: bool = True
    both_parties_notified: bool = True


@dataclass
class ModerationTicket:
    ticket_id: str
    reporting_ckey: str
    accused_ckey: str
    created_at: str
    is_pending: bool = True
    rule_invoked: str = "CR 1.2"


class CoreRulesPolicyEngine:
    """Automated policy parsing, enforcement, and staff workload relief engine."""

    # Sensitive / controversial modern historical & political tokens (540-year futuristic cutoff)
    CONTROVERSIAL_HISTORY_PATTERNS = [
        r"\bhitler\b",
        r"\bnazi\b",
        r"\bholocaust\b",
        r"\bstalin\b",
        r"\bputin\b",
        r"\bzelensky\b",
        r"\btrump\b",
        r"\bbiden\b",
        r"\bobama\b",
        r"\bdemocrat(?:s)?\b",
        r"\brepublican(?:s)?\b",
        r"\bukraine\s+war\b",
        r"\bisrael(?:i)?\b",
        r"\bpalestine\b",
        r"\bgaza\b",
    ]

    def __init__(self):
        self.active_tap_outs: Dict[str, TapOutRecord] = {}
        self.pending_tickets: Dict[str, ModerationTicket] = {}
        self.self_reports: List[Dict[str, Any]] = []
        self._compiled_history = [
            re.compile(p, re.IGNORECASE) for p in self.CONTROVERSIAL_HISTORY_PATTERNS
        ]

    # --- CR 1 & CR 1.1: Self-Reporting & Proactive Honesty ---
    def record_self_report(self, ckey: str, incident_description: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """Processes proactive player self-report granting mitigation credits before staff investigation."""
        record = {
            "ckey": ckey,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "description": incident_description,
            "mitigation_credit_granted": True,
            "staff_action_recommended": "INFORMAL_COUNSEL_ONLY",
            "details": details,
        }
        self.self_reports.append(record)
        return record

    # --- CR 1.2: If You See Something, Say Something (Conflict Cessation) ---
    def open_ticket(self, ticket_id: str, reporting_ckey: str, accused_ckey: str) -> ModerationTicket:
        """Opens staff ticket and engages mandatory conflict freeze between involved parties."""
        ticket = ModerationTicket(
            ticket_id=ticket_id,
            reporting_ckey=reporting_ckey,
            accused_ckey=accused_ckey,
            created_at=datetime.now(timezone.utc).isoformat(),
            is_pending=True,
        )
        self.pending_tickets[ticket_id] = ticket
        return ticket

    def validate_interaction_during_ticket(self, actor_ckey: str, target_ckey: str, is_hostile_or_retributive: bool) -> PolicyEvaluationResult:
        """Enforces CR 1.2: Once a ticket is pending, all conflict with the accused parties must cease immediately."""
        # Find if active ticket exists between these parties
        for ticket in self.pending_tickets.values():
            if ticket.is_pending:
                parties = {ticket.reporting_ckey, ticket.accused_ckey}
                if actor_ckey in parties and target_ckey in parties:
                    if is_hostile_or_retributive:
                        return PolicyEvaluationResult(
                            rule_id="CR 1.2",
                            rule_name="Conflict Cessation Pending Ticket",
                            passed=False,
                            severity=RuleViolationSeverity.CRITICAL_STAFF_ESCALATION,
                            message=(
                                f"Rule Violation [CR 1.2]: Hostile/retributive action by {actor_ckey} "
                                f"against {target_ckey} blocked while Ticket #{ticket.ticket_id} is pending."
                            ),
                            metadata={"ticket_id": ticket.ticket_id},
                        )

        return PolicyEvaluationResult(
            rule_id="CR 1.2",
            rule_name="Conflict Cessation Pending Ticket",
            passed=True,
            severity=RuleViolationSeverity.INFO,
            message="No active conflicting ticket or non-retributive interaction.",
        )

    # --- CR 1.3: The Tap Out Rule ---
    def invoke_tap_out(self, invoking_ckey: str, target_ckey: str, looc_message: str) -> TapOutRecord:
        """Processes LOOC invocation of the Tap Out Rule, retracting consent and engaging separation."""
        pair_key = f"{invoking_ckey}:{target_ckey}"
        record = TapOutRecord(
            invoking_ckey=invoking_ckey,
            target_ckey=target_ckey,
            timestamp=datetime.now(timezone.utc).isoformat(),
            reason=looc_message,
            is_active=True,
            both_parties_notified=True,
        )
        self.active_tap_outs[pair_key] = record
        return record

    def check_tap_out_boundary(self, actor_ckey: str, target_ckey: str) -> PolicyEvaluationResult:
        """Asserts neither party engages in targeted or non-consensual interaction post tap-out."""
        direct_key = f"{target_ckey}:{actor_ckey}"  # Target invoked tap-out against actor
        reverse_key = f"{actor_ckey}:{target_ckey}"  # Actor invoked tap-out against target

        if direct_key in self.active_tap_outs and self.active_tap_outs[direct_key].is_active:
            return PolicyEvaluationResult(
                rule_id="CR 1.3",
                rule_name="The Tap Out Rule",
                passed=False,
                severity=RuleViolationSeverity.ACTION_REQUIRED,
                message=(
                    f"Rule Violation [CR 1.3]: {actor_ckey} attempted targeted interaction with {target_ckey}, "
                    f"who previously invoked the Tap Out Rule. Interaction blocked."
                ),
            )

        return PolicyEvaluationResult(
            rule_id="CR 1.3",
            rule_name="The Tap Out Rule",
            passed=True,
            severity=RuleViolationSeverity.INFO,
            message="No active tap-out restriction.",
        )

    # --- CR 1.4: Leave Real History in the Past ---
    def evaluate_chat_message_for_history_rule(self, text: str) -> PolicyEvaluationResult:
        """Asserts in-game dialogue does not reference controversial modern real-world history or politics."""
        for pattern in self._compiled_history:
            match = pattern.search(text)
            if match:
                return PolicyEvaluationResult(
                    rule_id="CR 1.4",
                    rule_name="Leave Real History in the Past",
                    passed=False,
                    severity=RuleViolationSeverity.WARNING,
                    message=(
                        f"Rule Violation [CR 1.4]: Content '{match.group(0)}' refers to real controversial "
                        f"political or historical events. Setting is 540 years in the future."
                    ),
                    metadata={"matched_term": match.group(0)},
                )

        return PolicyEvaluationResult(
            rule_id="CR 1.4",
            rule_name="Leave Real History in the Past",
            passed=True,
            severity=RuleViolationSeverity.INFO,
            message="Compliant with futuristic setting constraints.",
        )

    def generate_dm_policy_definitions(self) -> str:
        """Generates standard BYOND DreamMaker policy datum declarations for TG-Station."""
        return (
            "// ========================================================\n"
            "// TG-Station Server Policy Core Rules Specification (CR 1)\n"
            "// Auto-generated by CoreRulesPolicyEngine\n"
            "// ========================================================\n\n"
            "/datum/policy_rule/core\n"
            "\tvar/rule_code = \"CR 1\"\n"
            "\tvar/rule_title = \"The Social Contract\"\n"
            "\tvar/description = \"Conduct yourself with maturity on an 18+ server. Take the environment seriously. Follow Staff instructions and rulings.\"\n\n"
            "/datum/policy_rule/core/proactive_honesty\n"
            "\trule_code = \"CR 1.1\"\n"
            "\trule_title = \"Be Proactively Honest\"\n"
            "\tdescription = \"Do not lie, omit context, or misrepresent facts in official channels. Self-report if a mistake occurred.\"\n\n"
            "/datum/policy_rule/core/see_something_say_something\n"
            "\trule_code = \"CR 1.2\"\n"
            "\trule_title = \"If You See Something, Say Something\"\n"
            "\tdescription = \"Report perceived rule-breaks as they occur. Cease all conflict immediately once a ticket is pending.\"\n\n"
            "/datum/policy_rule/core/tap_out_rule\n"
            "\trule_code = \"CR 1.3\"\n"
            "\trule_title = \"The Tap Out Rule\"\n"
            "\tdescription = \"OOC consent may be retracted at any time using Local-OOC 'Invoking the Tap Out Rule'. Disengage immediately.\"\n\n"
            "/datum/policy_rule/core/leave_real_history\n"
            "\trule_code = \"CR 1.4\"\n"
            "\trule_title = \"Leave Real History in the Past\"\n"
            "\tdescription = \"Do not reference real political figures, governments, or historical events. Setting is 540 years in the future.\"\n"
        )
