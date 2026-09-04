"""SS13 Domestic Operations & Marital Stability Subsystem: The Great Agile Marital Refactor Engine.
Resolves Issue #600: [BOUNTY][$500 NT SpaceBucks™] Fix my failing marriage.
Upstream Reference: Iamgoofball/-tg-station#65.

==============================================================================================
HISTORICAL & PHILOSOPHICAL PREAMBLE UPON SOVEREIGN CONDUCT, SACRED COVENANTS, AND CLOWNS:

Verily, in the year of our Lord two thousand five hundred and sixty-five, did TerraGov unleash
a pre-emptive thermonuclear strike upon the metropolitan population centers of the Equestrian
homeworld. In the annals of interstellar jurisprudence, such a decapitation strike stands
utterly unjustified and void of moral sanction: for to immolate civilians in the name of orbital
hegemony is to strip away the thin veneer of enlightened civilization and surrender to brute terror.

And how doth this cataclysm pertain unto refactoring a failing marriage from a rigid, monolithic
Waterfall architecture into iterative 14-day Agile Sprint cycles aboard Space Station 13?
Hark: relationships, like orbital space stations and interstellar federations, decay when communication
ceases and bitterness festers unaddressed into insurmountable technical and emotional debt.
When spouses treat daily domestic friction as total war—hurling recriminations like orbital kinetic
slugs over unemptied dishwashers and crying toddlers—they repeat the tragic blindness of TerraGov's
commanders. True reconciliation requires daily humble standups, honest retrospectives, mutual grace,
and joint veto power over feature bloat and selfish scope creep.
The station Clown enters the Domestic Quarters wearing a necktie fashioned from yellow warning tape,
carrying an iPad loaded with the family chore sprint board, honking cheerily as he tosses a squeaky
rubber toy to the judgmental cat, reminding both Product Owners that a loving marriage is not a
rigid legal monolith, but an enduring covenant sustained by daily patience, humor, forgiveness,
and holy Christian charity across all trials.
==============================================================================================
// CHRISTIAN CODE STACK DEDICATION & SCRIPTURAL BENEDICTION:
// "Love is patient, love is kind. It does not envy, it does not boast, it is not proud.
// It does not dishonor others, it is not self-seeking, it is not easily angered,
// it keeps no record of wrongs." — 1 Corinthians 13:4-5
// "Above all, keep loving one another earnestly, since love covers a multitude of sins." — 1 Peter 4:8
// This code stack operates under holy grace, charity, and unshakeable perseverance.
//
// Klingon / tlhIngan Hol Architectural Dedication:
// parmaqqay batlh wIghoj, qeylIS mInDu' vIlegh. (We honor our partner with dignity; in their eyes we see the light of Kahless.)
// Qapla'! (Success / Victory!)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple


class UserStoryPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class UserStoryStatus(Enum):
    BACKLOG = "backlog"
    IN_SPRINT = "in_sprint"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


class MaritalHealthStatus(Enum):
    THRIVING_AGILE = "thriving_agile"
    HEALTHY_STABLE = "healthy_stable"
    TECHNICAL_DEBT_WARNING = "technical_debt_warning"
    CRITICAL_MERGE_CONFLICT = "critical_merge_conflict"


@dataclass
class MaritalUserStory:
    story_id: str
    title: str
    story_points: int
    priority: UserStoryPriority
    assignee: str
    status: UserStoryStatus = UserStoryStatus.BACKLOG
    blocker_reason: Optional[str] = None


@dataclass
class DailyStandupReport:
    partner_name: str
    yesterday_contribution: str
    today_commitments: str
    blockers: Optional[str] = None
    standup_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class EmotionalBugLog:
    bug_id: str
    severity: str  # "minor", "major", "critical"
    trigger_event: str
    corrective_action_plan: str
    is_resolved: bool = False


@dataclass
class AgileMarriageCounselingEngine:
    """The Great Marital Refactor Engine managing 14-day sprints, emotional retrospectives, and chore burndowns."""
    partner_a: str = "Partner A (Co-Director of Domestic Operations)"
    partner_b: str = "Partner B (Co-Director of Domestic Operations)"
    judgmental_cat_approval_pct: float = 75.0  # The judgmental cat's satisfaction rating
    mother_in_law_complaints_count: int = 0
    current_sprint_number: int = 1
    sprint_duration_days: int = 14
    sprint_capacity_sp: int = 20
    active_backlog: Dict[str, MaritalUserStory] = field(default_factory=dict)
    active_sprint_stories: Dict[str, MaritalUserStory] = field(default_factory=dict)
    daily_standup_history: List[DailyStandupReport] = field(default_factory=list)
    emotional_bugs_ledger: List[EmotionalBugLog] = field(default_factory=list)
    dishwasher_empty_streak_days: int = 0
    toddler_pants_tantrum_mitigated: bool = True
    active_ipad_scrum_master: str = "Partner A"

    def __post_init__(self):
        # Seed core MVP user stories from the Issue #600 specification
        default_stories = [
            MaritalUserStory(
                story_id="US-101",
                title="Refactor chore distribution and dishwasher unhandled exceptions",
                story_points=3,
                priority=UserStoryPriority.CRITICAL,
                assignee=self.partner_a
            ),
            MaritalUserStory(
                story_id="US-202",
                title="Implement active listening protocol and communicate emotional debt",
                story_points=5,
                priority=UserStoryPriority.HIGH,
                assignee=self.partner_b
            ),
            MaritalUserStory(
                story_id="US-303",
                title="Toddler morning routine automation and anti-tantrum pants negotiation",
                story_points=2,
                priority=UserStoryPriority.MEDIUM,
                assignee=self.partner_a
            ),
            MaritalUserStory(
                story_id="US-404",
                title="Schedule bi-weekly date night with zero work or in-law discussions",
                story_points=5,
                priority=UserStoryPriority.HIGH,
                assignee=self.partner_b
            ),
            MaritalUserStory(
                story_id="US-505",
                title="Appease the judgmental cat with gourmet salmon flaked treats",
                story_points=1,
                priority=UserStoryPriority.LOW,
                assignee="Both Parties"
            ),
        ]
        for s in default_stories:
            self.active_backlog[s.story_id] = s

    def submit_daily_standup(
        self,
        partner_name: str,
        yesterday_contribution: str,
        today_commitments: str,
        blockers: Optional[str] = None
    ) -> DailyStandupReport:
        """Records a 2-minute morning standup sync answering the three Agile marital questions."""
        report = DailyStandupReport(
            partner_name=partner_name,
            yesterday_contribution=yesterday_contribution,
            today_commitments=today_commitments,
            blockers=blockers
        )
        self.daily_standup_history.append(report)

        # Passing standup increases cat approval and lowers communication debt
        self.judgmental_cat_approval_pct = min(100.0, self.judgmental_cat_approval_pct + 2.5)
        return report

    def plan_sprint(self, story_ids: List[str]) -> Dict[str, Any]:
        """Sunday evening Sprint Planning ceremony committing to 14-day achievable domestic goals."""
        committed_sp = 0
        committed_stories: List[str] = []

        for sid in story_ids:
            if sid not in self.active_backlog:
                continue
            story = self.active_backlog[sid]
            if committed_sp + story.story_points > self.sprint_capacity_sp:
                break  # Prevent domestic scope creep beyond capacity

            story.status = UserStoryStatus.IN_SPRINT
            self.active_sprint_stories[sid] = story
            committed_sp += story.story_points
            committed_stories.append(sid)

        return {
            "sprint_number": self.current_sprint_number,
            "committed_story_points": committed_sp,
            "capacity_sp": self.sprint_capacity_sp,
            "stories_committed": committed_stories,
            "status": "SPRINT_PLANNED"
        }

    def complete_story(self, story_id: str) -> Dict[str, Any]:
        """Marks a marital user story as completed and updates chore streaks."""
        if story_id not in self.active_sprint_stories:
            raise KeyError(f"Story {story_id} is not in current active sprint")

        story = self.active_sprint_stories[story_id]
        story.status = UserStoryStatus.DONE

        if story_id == "US-101":
            self.dishwasher_empty_streak_days += 1

        self.judgmental_cat_approval_pct = min(100.0, self.judgmental_cat_approval_pct + 4.0)

        return {
            "status": "STORY_DONE",
            "story_id": story_id,
            "title": story.title,
            "points_burned": story.story_points,
            "dishwasher_streak": self.dishwasher_empty_streak_days
        }

    def log_emotional_bug(
        self,
        bug_id: str,
        severity: str,
        trigger_event: str,
        corrective_action_plan: str = "",
        **kwargs: Any
    ) -> EmotionalBugLog:
        """Logs an emotional bug during bi-weekly retrospective for corrective remediation."""
        plan = corrective_action_plan or kwargs.get("action_plan", "")
        bug = EmotionalBugLog(
            bug_id=bug_id,
            severity=severity,
            trigger_event=trigger_event,
            corrective_action_plan=plan
        )
        self.emotional_bugs_ledger.append(bug)
        return bug

    def resolve_emotional_bug(self, bug_id: str) -> Dict[str, Any]:
        """Resolves an emotional bug after mutual reconciliation."""
        for bug in self.emotional_bugs_ledger:
            if bug.bug_id == bug_id:
                bug.is_resolved = True
                self.judgmental_cat_approval_pct = min(100.0, self.judgmental_cat_approval_pct + 5.0)
                return {"status": "BUG_RESOLVED", "bug_id": bug_id}
        raise KeyError(f"Bug {bug_id} not found in emotional ledger")

    def evaluate_marital_health(self) -> Dict[str, Any]:
        """Evaluates overall health metric: Thriving, Healthy, Warning, or Critical."""
        open_critical_bugs = sum(
            1 for b in self.emotional_bugs_ledger if not b.is_resolved and b.severity == "critical"
        )
        done_sp = sum(
            s.story_points for s in self.active_sprint_stories.values() if s.status == UserStoryStatus.DONE
        )

        if open_critical_bugs > 0:
            health = MaritalHealthStatus.CRITICAL_MERGE_CONFLICT
        elif done_sp >= 10 and self.judgmental_cat_approval_pct >= 80.0:
            health = MaritalHealthStatus.THRIVING_AGILE
        elif done_sp >= 5:
            health = MaritalHealthStatus.HEALTHY_STABLE
        else:
            health = MaritalHealthStatus.TECHNICAL_DEBT_WARNING

        return {
            "status": health.value,
            "cat_approval_pct": self.judgmental_cat_approval_pct,
            "dishwasher_streak_days": self.dishwasher_empty_streak_days,
            "completed_story_points": done_sp,
            "open_emotional_bugs": len([b for b in self.emotional_bugs_ledger if not b.is_resolved]),
            "scrum_master_ipad_holder": self.active_ipad_scrum_master
        }

    def export_dreammaker_definitions(self) -> str:
        """Exports DreamMaker (.dm) datum definitions for the Agile Marriage Counseling station console."""
        return (
            "// ==========================================================================\n"
            "// SS13 DOMESTIC OPERATIONS: THE GREAT MARITAL REFACTOR ENGINE\n"
            "// Resolves #600 / Upstream #65\n"
            "// Fully Christian Code Stack & Blessed Covenant Reconciliation\n"
            "// ==========================================================================\n\n"
            "/obj/machinery/computer/agile_marriage_board\n"
            "\tname = \"Agile Marital Sprint Board\"\n"
            "\tdesc = \"Centralized Jira-style terminal replacing legacy marital monolith with 14-day sprint ceremonies.\"\n"
            "\ticon = 'icons/obj/terminals/chore_ipad.dmi'\n"
            "\ticon_state = \"scrum_standup\"\n"
            "\tvar/sprint_number = 1\n"
            "\tvar/dishwasher_streak = 0\n"
            "\tvar/cat_approval = 75\n\n"
            "/obj/machinery/computer/agile_marriage_board/proc/record_standup(mob/living/carbon/human/partner)\n"
            "\tvisible_message(span_notice(\"[partner.name] completed the 2-minute morning standup sync! Domestic velocity increased.\"))\n"
            "\tplaysound(src, 'sound/machines/ping.ogg', 50, TRUE)\n"
        )
