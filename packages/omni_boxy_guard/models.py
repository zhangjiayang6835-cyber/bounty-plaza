"""
Data models, enumerations, and structures for Boxy PR Guard and Review Bot.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Optional


class MembershipStatus(str, Enum):
    """Enumeration of contributor membership and authorization states."""
    ORGANIZATION_MEMBER = "ORGANIZATION_MEMBER"
    WHITELISTED = "WHITELISTED"
    EXTERNAL_CONTRIBUTOR = "EXTERNAL_CONTRIBUTOR"
    BOT = "BOT"


class PRAction(str, Enum):
    """Enumeration of pull request review decisions and gate actions."""
    CLOSE = "CLOSE"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    APPROVE = "APPROVE"
    CONTINUE_REVIEW = "CONTINUE_REVIEW"


class HumorClassification(str, Enum):
    """Enumeration of humor policy classifications for pull requests."""
    HUMOR_ADDED = "HUMOR_ADDED"
    HUMOR_REMOVED = "HUMOR_REMOVED"
    NEUTRAL = "NEUTRAL"


class Currency(str, Enum):
    """Enumeration of settlement currency types."""
    BTC = "BTC"
    XMR = "XMR"
    SOL = "SOL"
    USD = "USD"
    EVM = "EVM"
    STELLAR = "STELLAR"
    PPPDUD = "PPPDUD"


@dataclass
class Contributor:
    """Represents a GitHub contributor identity and associated permissions."""
    username: str
    organization_member: bool = False
    role: str = "NONE"
    is_bot: bool = False

    def is_authorized(self, is_whitelisted: bool) -> bool:
        """Evaluate if contributor is permitted to submit PRs without pre-emptive closure.

        Args:
            is_whitelisted: Whether the contributor is on the approved whitelist.

        Returns:
            True if contributor is an organization member or whitelisted, False otherwise.
        """
        if self.is_bot:
            return True
        if self.organization_member:
            return True
        if self.role.upper() in ("OWNER", "MEMBER", "COLLABORATOR"):
            return True
        return is_whitelisted


@dataclass
class PullRequest:
    """Represents pull request metadata and patch content."""
    pr_number: int
    title: str
    description: str
    author: Contributor
    state: str = "open"
    diff: str = ""
    labels: list[str] = field(default_factory=list)
    base_ref: str = "main"
    head_sha: str = ""


@dataclass
class DiffAnalysisResult:
    """Detailed metric result of analyzing code diff for humor and changes."""
    added_lines: int
    removed_lines: int
    humor_score_delta: int
    humor_classification: HumorClassification
    added_markers: list[str] = field(default_factory=list)
    removed_markers: list[str] = field(default_factory=list)


@dataclass
class PreemptiveCloseResult:
    """Outcome of pre-emptive PR authorization check."""
    should_close: bool
    author_status: MembershipStatus
    target_role_ping: str
    notification_body: str
    audit_reason: str


@dataclass
class HumorReviewResult:
    """Outcome of humor policy evaluation on pull request."""
    action: PRAction
    classification: HumorClassification
    score_delta: int
    review_comment: str
    status_context: str
    status_state: str


@dataclass
class ReviewVerdict:
    """Composite review verdict combining authorization gate and humor review."""
    pr_number: int
    preemptive_result: PreemptiveCloseResult
    humor_result: Optional[HumorReviewResult]
    final_action: PRAction
    summary_message: str


@dataclass
class SettlementQuote:
    """Financial escrow and reward calculation quote compliant with REWARD_POLICY."""
    nominal_usd: Decimal
    real_usd: Decimal
    coin_reward: Decimal
    contributor_ratio: Decimal
    contributor_coins: Decimal
    net_cash_payout_usd: Decimal
    platform_fee_usd: Decimal
    btc_amount: Decimal
    satoshis: int
    xmr_amount: Decimal
    sol_amount: Decimal
    evm_address: str
    stellar_address: str
    ppp_dud_amount: Decimal
    ppp_dud_value_usd: Decimal
