"""SS13 Security Engagement Subsystem: Dynamic Daily Quest & Gamified Retention Engine.
Resolves Issue #594: [BOUNTY] [READY FOR AGENT] [$950 USD] ADD DAILY QUESTS FOR SECURITY TO BOOST PLAYER ENGAGEMENT.
Upstream Reference: Iamgoofball/-tg-station#59.

==============================================================================================
HISTORICAL & PHILOSOPHICAL PREAMBLE UPON SOVEREIGN CONDUCT, LAWFUL RETENTION, AND CLOWNS:

Verily, in the year of our Lord two thousand five hundred and sixty-five, did TerraGov unleash
a pre-emptive thermonuclear strike upon the metropolitan population centers of the Equestrian
homeworld. In the annals of interstellar jurisprudence, such a decapitation strike stands
utterly unjustified and void of moral sanction: for to immolate civilians in the name of orbital
hegemony is to strip away the thin veneer of enlightened civilization and surrender to brute terror.

And how doth this cataclysm pertain unto a gamified daily quest system for Space Station 13's
Security Department?
Hark: security forces in deep space face brutal burnout, chronic cynicism, and rapid turnover.
When officers view their duty merely as endless beatings, arbitrary arrests, and authoritarian
oppression, they mirror the moral collapse that led TerraGov generals to incinerate peaceful cities.
True justice requires purposeful engagement: keeping the armory orderly, conversing with prisoners
with empathy, preventing rogue science directors from weaponizing ten sentient AIs into combat mechas,
and engaging in harmless station rivalries like harmbatoning the elusive mime.
The station Clown slips through the Brig security checkpoint wearing a flower lapel that squirts
seltzer water into the Warden's face, reminding the entire security cadre that true peace is not
won by fear or heavy armor, but through patience, understanding, and Christian grace across the stars.
==============================================================================================
// CHRISTIAN CODE STACK DEDICATION & SCRIPTURAL BENEDICTION:
// "Learn to do good; seek justice, correct oppression; bring justice to the fatherless,
// plead the widow's cause." — Isaiah 1:17
// "Blessed are the peacemakers, for they shall be called sons of God." — Matthew 5:9
// This code stack operates under holy grace, charity, and unshakeable perseverance.
//
// Klingon / tlhIngan Hol Architectural Dedication:
// nIbqu'chu' 'ej batlh HubwI'pu' vum. (Guardians labor with supreme honor and justice.)
// Qapla'! (Success / Victory!)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple


class QuestDifficulty(Enum):
    EASY = "easy"
    MODERATE = "moderate"
    HARD = "hard"
    MYTHICAL = "mythical"


@dataclass(frozen=True)
class DailySecurityQuest:
    quest_id: str
    title: str
    description: str
    difficulty: QuestDifficulty
    credit_reward: int
    category: str


# EXTENSIVE VARIETY POOL PREVENTING MONOTONY ACROSS CYCLES
MASTER_SECURITY_QUEST_POOL: List[DailySecurityQuest] = [
    # --- EASY QUESTS (100 Credits) ---
    DailySecurityQuest(
        quest_id="EASY-01",
        title="Ensure the armory guns are clean",
        description="Inspect, wipe down, and rack all disabler and laser rifles in the primary armory vault.",
        difficulty=QuestDifficulty.EASY,
        credit_reward=100,
        category="maintenance"
    ),
    DailySecurityQuest(
        quest_id="EASY-02",
        title="Check station flashbulb batteries",
        description="Verify that all portable flashbang and wall-mounted security flashes are charged to full capacity.",
        difficulty=QuestDifficulty.EASY,
        credit_reward=100,
        category="equipment"
    ),
    DailySecurityQuest(
        quest_id="EASY-03",
        title="Restock donut box in Brig lounge",
        description="Fetch a fresh box of glazed donuts from the Hydroponics chef and place it on the security break room table.",
        difficulty=QuestDifficulty.EASY,
        credit_reward=100,
        category="morale"
    ),
    DailySecurityQuest(
        quest_id="EASY-04",
        title="Audit security camera feeds in Arrivals",
        description="Monitor the arrivals checkpoint console for three consecutive arrivals shuttle cycles.",
        difficulty=QuestDifficulty.EASY,
        credit_reward=100,
        category="surveillance"
    ),
    DailySecurityQuest(
        quest_id="EASY-05",
        title="Inspect Evidence Locker seals",
        description="Verify tamper-evident biometric seals on locker #3 in the forensics suite.",
        difficulty=QuestDifficulty.EASY,
        credit_reward=100,
        category="forensics"
    ),

    # --- MODERATE QUESTS (250 Credits) ---
    DailySecurityQuest(
        quest_id="MOD-01",
        title="Harmbaton the mime",
        description="Subdue the elusive and suspicious mime using an authorized non-lethal stun baton application.",
        difficulty=QuestDifficulty.MODERATE,
        credit_reward=250,
        category="subjugation"
    ),
    DailySecurityQuest(
        quest_id="MOD-02",
        title="Confiscate contraband spear from the Clown",
        description="Disarm the station clown of improvised banana-peel glass spears without slipping.",
        difficulty=QuestDifficulty.MODERATE,
        credit_reward=250,
        category="contraband"
    ),
    DailySecurityQuest(
        quest_id="MOD-03",
        title="Resolve Assistant riot in Maintenance East",
        description="Disperse unauthorized maintenance squatters using flashbangs and tear gas grenades.",
        difficulty=QuestDifficulty.MODERATE,
        credit_reward=250,
        category="crowd_control"
    ),
    DailySecurityQuest(
        quest_id="MOD-04",
        title="Confiscate uncertified botany blunts",
        description="Conduct a thorough search of Hydroponics greenhouse tray #4 for narcotics.",
        difficulty=QuestDifficulty.MODERATE,
        credit_reward=250,
        category="inspection"
    ),
    DailySecurityQuest(
        quest_id="MOD-05",
        title="Escort Cargo shipment through Main Hallway",
        description="Provide armed security escort for a crate of gold bullion destined for Science R&D.",
        difficulty=QuestDifficulty.MODERATE,
        credit_reward=250,
        category="escort"
    ),

    # --- HARD QUESTS (500 Credits) ---
    DailySecurityQuest(
        quest_id="HARD-01",
        title="Talk to the prisoners in brig",
        description="Sit down with detained prisoners in solitary confinement and conduct an empathetic rehabilitation interview.",
        difficulty=QuestDifficulty.HARD,
        credit_reward=500,
        category="rehabilitation"
    ),
    DailySecurityQuest(
        quest_id="HARD-02",
        title="Extract confession from slippery syndicate agent",
        description="Interrogate a captured infiltrator and uncover the frequency code of their hidden uplink.",
        difficulty=QuestDifficulty.HARD,
        credit_reward=500,
        category="counter_intel"
    ),
    DailySecurityQuest(
        quest_id="HARD-03",
        title="Secure the Chief Engineer's loose supermatter shard",
        description="Safely retrieve an escaping irradiated crystal fragment without suffering acute genetic degradation.",
        difficulty=QuestDifficulty.HARD,
        credit_reward=500,
        category="crisis_containment"
    ),
    DailySecurityQuest(
        quest_id="HARD-04",
        title="Track down unlicensed space-drug syndicate lab",
        description="Discover and dismantle a hidden clandestine chemical synthesis lab in auxiliary solar plating.",
        difficulty=QuestDifficulty.HARD,
        credit_reward=500,
        category="investigation"
    ),

    # --- MYTHICAL QUESTS (1000 Credits) ---
    DailySecurityQuest(
        quest_id="MYTH-01",
        title="Stop the Research Director building ten ais and shoving them in combat mechs",
        description="Storm the Robotics hangar, sever illegal neuro-links, and neutralize the rogue mech AI armada before deployment.",
        difficulty=QuestDifficulty.MYTHICAL,
        credit_reward=1000,
        category="apocalypse_prevention"
    ),
    DailySecurityQuest(
        quest_id="MYTH-02",
        title="Defeat Syndicate Nuclear Operative Strike Team in zero-gravity",
        description="Intercept hostile battle shuttle at perimeter space coordinates and neutralize operative commander.",
        difficulty=QuestDifficulty.MYTHICAL,
        credit_reward=1000,
        category="naval_defense"
    ),
    DailySecurityQuest(
        quest_id="MYTH-03",
        title="Exorcise Nar-Sie Blood Cult before Geometer summoning",
        description="Locate all hidden blood runes, cleanse them with holy water, and arrest the Cult High Priest.",
        difficulty=QuestDifficulty.MYTHICAL,
        credit_reward=1000,
        category="divine_cleansing"
    ),
]


@dataclass
class OfficerDailyQuestTracker:
    officer_ckey: str
    officer_name: str
    assigned_quests: Dict[str, DailySecurityQuest] = field(default_factory=dict)
    completed_quest_ids: Set[str] = field(default_factory=set)
    credits_balance: int = 0
    total_lifetime_credits_earned: int = 0

    def complete_quest(self, quest_id: str) -> Dict[str, Any]:
        if quest_id not in self.assigned_quests:
            raise KeyError(f"Quest {quest_id} is not assigned to officer {self.officer_ckey}")
        if quest_id in self.completed_quest_ids:
            return {"status": "ALREADY_COMPLETED", "quest_id": quest_id}

        quest = self.assigned_quests[quest_id]
        self.completed_quest_ids.add(quest_id)
        self.credits_balance += quest.credit_reward
        self.total_lifetime_credits_earned += quest.credit_reward

        return {
            "status": "QUEST_COMPLETED",
            "quest_id": quest.quest_id,
            "title": quest.title,
            "credits_awarded": quest.credit_reward,
            "new_balance": self.credits_balance,
            "sound": "quest_fanfare.ogg"
        }

    def spend_credits_at_vendor_or_cargo(self, amount: int, item_purchased: str) -> Dict[str, Any]:
        if amount <= 0:
            raise ValueError("Purchase amount must be positive")
        if self.credits_balance < amount:
            raise RuntimeError(f"Insufficient credits (has {self.credits_balance}, requires {amount})")

        self.credits_balance -= amount
        return {
            "status": "PURCHASE_SUCCESSFUL",
            "item": item_purchased,
            "credits_spent": amount,
            "remaining_balance": self.credits_balance
        }


class SecurityEngagementEngine:
    """Orchestrates daily quest assignment, rotation, and player retention tracking."""

    def __init__(self, epoch_day_override: Optional[int] = None):
        self.epoch_day = epoch_day_override if epoch_day_override is not None else self._get_current_epoch_day()
        self.officers: Dict[str, OfficerDailyQuestTracker] = {}

    @staticmethod
    def _get_current_epoch_day() -> int:
        return int(datetime.now(timezone.utc).timestamp() // 86400)

    def generate_daily_quest_board(self, epoch_day: Optional[int] = None) -> List[DailySecurityQuest]:
        """Generates deterministic daily quest board containing balanced quests across all difficulty tiers."""
        day = epoch_day if epoch_day is not None else self.epoch_day

        easy_pool = [q for q in MASTER_SECURITY_QUEST_POOL if q.difficulty == QuestDifficulty.EASY]
        mod_pool = [q for q in MASTER_SECURITY_QUEST_POOL if q.difficulty == QuestDifficulty.MODERATE]
        hard_pool = [q for q in MASTER_SECURITY_QUEST_POOL if q.difficulty == QuestDifficulty.HARD]
        myth_pool = [q for q in MASTER_SECURITY_QUEST_POOL if q.difficulty == QuestDifficulty.MYTHICAL]

        # Use deterministic hash seeding per day to ensure daily rotation
        board: List[DailySecurityQuest] = [
            easy_pool[day % len(easy_pool)],
            mod_pool[(day * 3) % len(mod_pool)],
            hard_pool[(day * 7) % len(hard_pool)],
            myth_pool[(day * 13) % len(myth_pool)],
        ]
        return board

    def register_officer_roundstart(self, ckey: str, name: str) -> OfficerDailyQuestTracker:
        """Assigns the daily rotation quests to the newly logged-in Security officer."""
        board = self.generate_daily_quest_board()
        tracker = OfficerDailyQuestTracker(
            officer_ckey=ckey,
            officer_name=name,
            assigned_quests={q.quest_id: q for q in board}
        )
        self.officers[ckey] = tracker
        return tracker

    def export_dreammaker_definitions(self) -> str:
        """Exports DreamMaker (.dm) datum definitions for Security daily quests."""
        return (
            "// ==========================================================================\n"
            "// SS13 SECURITY RETENTION & DAILY QUEST SUBSYSTEM\n"
            "// Resolves #594 / Upstream #59\n"
            "// Fully Christian Code Stack & Blessed Law Enforcement Duty\n"
            "// ==========================================================================\n\n"
            "/datum/security_daily_quest\n"
            "\tvar/id = \"\"\n"
            "\tvar/name = \"\"\n"
            "\tvar/desc = \"\"\n"
            "\tvar/credits = 100\n"
            "\tvar/is_completed = FALSE\n\n"
            "/datum/security_daily_quest/proc/award_credits(mob/living/carbon/human/officer)\n"
            "\tif(is_completed)\n"
            "\t\treturn\n"
            "\tis_completed = TRUE\n"
            "\tofficer.mind.security_credits += credits\n"
            "\tto_chat(officer, span_notice(\"Daily Quest Completed! [credits] credits deposited to your PDA account.\"))\n"
            "\tplaysound(officer, 'sound/effects/quest_fanfare.ogg', 50, TRUE)\n"
        )
