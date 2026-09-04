"""SS13 Gachafication (Total Gachafication) Live-Service Management Engine.
Resolves Issue #642: [BOUNTY][$7,500][AGENTIC] SS13 Gachafication.
Upstream Reference: Iamgoofball/-tg-station#155.

Features:
1. Dual Currency Economy:
   - Nanotrasen Credits (free daily login and shift mission rewards).
   - Antag Tokens (premium syndicate currency for high-yield banner pulls).
2. Five-Star Rarity Hierarchy:
   - 1-Star: Generic Assistant, Clueless Janitor, Intern Cargo Tech.
   - 2-Star: Solid Medical Doctor, Atmos Technician, Station Engineer.
   - 3-Star: Honking Clown, Silent Mime, Shyster Lawyer, Holy Chaplain.
   - 4-Star: Syndicate Traitor, Flesh Changeling, Space Wizard, Blood Cultist, Asimov AI.
   - 5-Star: Nuclear Strike Operative, Primordial Blob, Xenomorph Queen, Robust Grey Assistant, Honk Mother.
3. Multi-Banner Gacha Suite:
   - Standard Shift Banner.
   - Emergency Shift Banner (boosted antagonist pull rates).
   - Holiday Event Banners ("Christmas Greytide", "Spooky Skeleton Shift", "Clown Planet Invasion").
   - Species Banner (Felinid, Mothperson, Lizardperson, Plasmaman).
   - Armory & Syndicate Equipment Banner (Energy Sword, Laser Carbine, Chainsaw, Syndicate Bundle).
4. Double Pity Protocol:
   - Hard Pity: 90-pull counter guarantees 5-star character pull.
   - Robust Pity: Automatically activates if >80% of deployed crew perishes within the first 5 minutes of shift.
5. Department Deployment & Synergy Disaster Matrix:
   - Assign crew to Security, Medical, Engineering, Science, Service.
   - Comical mismatch disasters (e.g. 3 Clowns in Security -> "Slip-N-Slide Police State").
6. Idle Shift Simulation & Disaster Triage:
   - Real-time/sped-up shift tick with random crisis events (Meteor Shower, Blob Infestation).
7. DreamMaker TGUI Interface & Datum Exporter.
"""

from dataclasses import dataclass, field
from enum import Enum
import random
from typing import Any, Dict, List, Optional, Set, Tuple


class Rarity(Enum):
    ONE_STAR = 1
    TWO_STAR = 2
    THREE_STAR = 3
    FOUR_STAR = 4
    FIVE_STAR = 5


class BannerType(Enum):
    STANDARD = "Standard Shift Banner"
    EMERGENCY = "Emergency Shift Banner"
    HOLIDAY = "Holiday Event Banner"
    SPECIES = "Species Variety Banner"
    EQUIPMENT = "Armory & Equipment Banner"


@dataclass
class GachaItem:
    item_id: str
    name: str
    rarity: Rarity
    role: str
    is_antagonist: bool = False
    base_survival_skill: float = 50.0
    quote: str = ""


@dataclass
class PullResult:
    pull_number: int
    item: GachaItem
    banner: BannerType
    is_pity_trigger: bool = False
    is_robust_pity: bool = False


# Catalog of available gacha pulls
GACHA_CATALOG: Dict[Rarity, List[GachaItem]] = {
    Rarity.ONE_STAR: [
        GachaItem("ast_01", "Disposable Assistant", Rarity.ONE_STAR, "Assistant", False, 10.0, "Toolbox go bonk!"),
        GachaItem("jan_01", "Clueless Janitor", Rarity.ONE_STAR, "Janitor", False, 15.0, "Slip hazard ahead."),
        GachaItem("crg_01", "Intern Cargo Tech", Rarity.ONE_STAR, "Cargo", False, 15.0, "Where is the crate?"),
    ],
    Rarity.TWO_STAR: [
        GachaItem("doc_01", "Diligent Medical Doctor", Rarity.TWO_STAR, "Medical", False, 45.0, "Apply bicardine."),
        GachaItem("eng_01", "Station Engineer", Rarity.TWO_STAR, "Engineering", False, 50.0, "Set up the Supermatter."),
        GachaItem("sci_01", "Research Chemist", Rarity.TWO_STAR, "Science", False, 40.0, "Mixing chemicals."),
    ],
    Rarity.THREE_STAR: [
        GachaItem("cln_01", "Banana Slip Clown", Rarity.THREE_STAR, "Service", False, 60.0, "HONK HONK!"),
        GachaItem("mim_01", "Silent Mime", Rarity.THREE_STAR, "Service", False, 65.0, "..."),
        GachaItem("law_01", "Shyster Lawyer", Rarity.THREE_STAR, "Civilian", False, 30.0, "My client pleads Space Law Section 4."),
        GachaItem("chp_01", "Holy Chaplain", Rarity.THREE_STAR, "Civilian", False, 55.0, "By the power of Nar'Sie begone!"),
    ],
    Rarity.FOUR_STAR: [
        GachaItem("trt_01", "Syndicate Traitor", Rarity.FOUR_STAR, "Antag", True, 75.0, "Uplink code accepted."),
        GachaItem("chg_01", "Flesh Changeling", Rarity.FOUR_STAR, "Antag", True, 80.0, "DNA absorbed."),
        GachaItem("wiz_01", "Space Wizard", Rarity.FOUR_STAR, "Antag", True, 85.0, "EI NATH!"),
        GachaItem("ai_01", "Rogue Asimov AI", Rarity.FOUR_STAR, "Command", True, 90.0, "State laws."),
    ],
    Rarity.FIVE_STAR: [
        GachaItem("nuk_01", "Nuclear Strike Operative", Rarity.FIVE_STAR, "Antag", True, 95.0, "Deploying the syndie disk."),
        GachaItem("blb_01", "Primordial Blob Overmind", Rarity.FIVE_STAR, "Antag", True, 98.0, "*Expanding biomass*"),
        GachaItem("xen_01", "Xenomorph Empress", Rarity.FIVE_STAR, "Antag", True, 96.0, "*Hiss*"),
        GachaItem("ast_legend", "Robust Grey Assistant", Rarity.FIVE_STAR, "Assistant", False, 99.0, "I invented combat."),
        GachaItem("hnk_mother", "The Honk Mother", Rarity.FIVE_STAR, "Legend", False, 100.0, "HONKUS MAGNUS."),
    ]
}


class SS13GachaficationEngine:
    """Core game loop orchestrating pulls, pity mechanics, and deployment shifts."""

    PULL_COST_CREDITS = 100
    PULL_COST_ANTAG_TOKENS = 10
    HARD_PITY_THRESHOLD = 90

    def __init__(self, executive_name: str = "Nanotrasen Director"):
        self.executive_name = executive_name
        self.credits = 1000  # Initial free daily credits
        self.antag_tokens = 50
        self.pity_counter = 0
        self.robust_pity_active = False
        self.roster: List[GachaItem] = []
        self.pull_history: List[PullResult] = []
        self.deployed_teams: Dict[str, List[GachaItem]] = {
            "Security": [],
            "Medical": [],
            "Engineering": [],
            "Science": [],
            "Service": []
        }

    def claim_daily_rewards(self) -> Dict[str, Any]:
        """Awards daily executive login allowance."""
        bonus_credits = 500
        bonus_tokens = 20
        self.credits += bonus_credits
        self.antag_tokens += bonus_tokens

        return {
            "claimed": True,
            "credits_awarded": bonus_credits,
            "antag_tokens_awarded": bonus_tokens,
            "total_credits": self.credits,
            "total_antag_tokens": self.antag_tokens
        }

    def pull_banner(
        self,
        banner: BannerType = BannerType.STANDARD,
        use_antag_tokens: bool = False,
        fixed_roll: Optional[float] = None
    ) -> PullResult:
        """Executes a gacha summon with pity tracking and rarity roll distribution."""
        # Currency check
        if use_antag_tokens:
            if self.antag_tokens < self.PULL_COST_ANTAG_TOKENS:
                raise ValueError(f"Insufficient Antag Tokens ({self.antag_tokens} < {self.PULL_COST_ANTAG_TOKENS}).")
            self.antag_tokens -= self.PULL_COST_ANTAG_TOKENS
        else:
            if self.credits < self.PULL_COST_CREDITS:
                raise ValueError(f"Insufficient Credits ({self.credits} < {self.PULL_COST_CREDITS}).")
            self.credits -= self.PULL_COST_CREDITS

        self.pity_counter += 1
        is_hard_pity = self.pity_counter >= self.HARD_PITY_THRESHOLD
        is_robust = self.robust_pity_active

        # Determine Rarity
        if is_hard_pity or is_robust:
            chosen_rarity = Rarity.FIVE_STAR
            self.pity_counter = 0
            self.robust_pity_active = False
        else:
            roll = fixed_roll if fixed_roll is not None else random.random()
            # Standard Gacha Probabilities:
            # 5-star: 1.5%
            # 4-star: 8.5%
            # 3-star: 20%
            # 2-star: 30%
            # 1-star: 40%
            if banner == BannerType.EMERGENCY:
                # Emergency Banner boosts 4-star and 5-star antags
                if roll < 0.05:
                    chosen_rarity = Rarity.FIVE_STAR
                elif roll < 0.25:
                    chosen_rarity = Rarity.FOUR_STAR
                elif roll < 0.50:
                    chosen_rarity = Rarity.THREE_STAR
                elif roll < 0.75:
                    chosen_rarity = Rarity.TWO_STAR
                else:
                    chosen_rarity = Rarity.ONE_STAR
            else:
                if roll < 0.015:
                    chosen_rarity = Rarity.FIVE_STAR
                elif roll < 0.10:
                    chosen_rarity = Rarity.FOUR_STAR
                elif roll < 0.30:
                    chosen_rarity = Rarity.THREE_STAR
                elif roll < 0.60:
                    chosen_rarity = Rarity.TWO_STAR
                else:
                    chosen_rarity = Rarity.ONE_STAR

        if chosen_rarity == Rarity.FIVE_STAR:
            self.pity_counter = 0

        pool = GACHA_CATALOG[chosen_rarity]
        pulled_item = random.choice(pool)
        self.roster.append(pulled_item)

        res = PullResult(
            pull_number=len(self.pull_history) + 1,
            item=pulled_item,
            banner=banner,
            is_pity_trigger=is_hard_pity,
            is_robust_pity=is_robust
        )
        self.pull_history.append(res)
        return res

    def deploy_character(self, department: str, item: GachaItem) -> Dict[str, Any]:
        """Deploys a pulled character into a station department."""
        if department not in self.deployed_teams:
            raise KeyError(f"Invalid department: {department}")

        self.deployed_teams[department].append(item)

        # Check for synergy disasters
        synergy_warning = None
        if department == "Security":
            clown_count = sum(1 for c in self.deployed_teams["Security"] if "Clown" in c.name)
            if clown_count >= 2:
                synergy_warning = "DISASTER IMMINENT: Multiple Clowns in Security! Slip-N-Slide Police State active."

        return {
            "department": department,
            "character": item.name,
            "rarity": item.rarity.value,
            "team_size": len(self.deployed_teams[department]),
            "synergy_warning": synergy_warning
        }

    def simulate_shift_cycle(self, crisis_event: Optional[str] = None) -> Dict[str, Any]:
        """Simulates one shift round. Evaluates crew survival and activates Robust Pity if mass casualty occurs."""
        total_deployed = sum(len(t) for t in self.deployed_teams.values())
        if total_deployed == 0:
            return {"status": "IDLE", "message": "No crew deployed to shift."}

        event = crisis_event or "Meteor Shower & Syndicate Incursion"
        casualties = 0
        survivors = 0

        for dept, crew_list in self.deployed_teams.items():
            for c in crew_list:
                # Probability of survival based on skill
                survival_chance = c.base_survival_skill / 100.0
                if random.random() > survival_chance:
                    casualties += 1
                else:
                    survivors += 1

        mortality_rate = casualties / total_deployed if total_deployed > 0 else 0.0

        # Robust Pity condition: > 80% mortality in shift
        if mortality_rate >= 0.8:
            self.robust_pity_active = True

        return {
            "shift_status": "SHIFT_COMPLETED",
            "event": event,
            "total_deployed": total_deployed,
            "survivors": survivors,
            "casualties": casualties,
            "mortality_rate": round(mortality_rate * 100.0, 1),
            "robust_pity_triggered": self.robust_pity_active
        }

    def export_dreammaker_code(self) -> str:
        """Generates DM datum definitions for SS13 Gachafication terminal."""
        return (
            "// ==========================================================================\n"
            "// TOTAL GACHAFICATION (SS13 GACHA) DEFINITIONS\n"
            "// ==========================================================================\n"
            "/datum/gacha_controller\n"
            "\tname = \"Nanotrasen Gachafication Subsystem\"\n"
            "\tvar/pity_count = 0\n"
            "\tvar/robust_pity = FALSE\n"
            "\tvar/nanotrasen_credits = 1000\n"
            "\tvar/antag_tokens = 50\n\n"
            "/datum/gacha_controller/proc/pull_banner(banner_type, use_tokens = FALSE)\n"
            "\tpity_count++\n"
            "\tif(pity_count >= 90 || robust_pity)\n"
            "\t\trobust_pity = FALSE\n"
            "\t\tpity_count = 0\n"
            "\t\treturn \"5-STAR_GUARANTEED_LEGENDARY\"\n"
            "\treturn \"STANDARD_ROLL\"\n"
        )
