"""Negative escrow and reverse ledger management.

Enforces REWARD_POLICY conversions for reverse liabilities, tracking platform
coin debits, multi-chain settlement proofs, and pledge waivers.
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import hashlib
import time
from typing import Dict, Any, Optional


class DebitStatus(str, Enum):
    """Lifecycle states of a reverse bounty debit."""
    PENDING = "pending"
    SETTLED_ONCHAIN = "settled_onchain"
    WAIVED_VIA_PLEDGE = "waived_via_pledge"
    DISPUTED = "disputed"


@dataclass
class DebitRecord:
    """Ledger record for reverse bounty obligation."""
    record_id: str
    user_id: str
    issue_id: int
    source_url: str
    amount_usd: Decimal
    coins_amount: Decimal
    status: DebitStatus
    created_at: float
    settled_at: Optional[float] = None
    tx_id: Optional[str] = None
    pledge_signature: Optional[str] = None
    blog_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert debit record to dictionary representation."""
        return {
            "record_id": self.record_id,
            "user_id": self.user_id,
            "issue_id": self.issue_id,
            "source_url": self.source_url,
            "amount_usd": str(self.amount_usd),
            "coins_amount": str(self.coins_amount),
            "status": self.status.value,
            "created_at": self.created_at,
            "settled_at": self.settled_at,
            "tx_id": self.tx_id,
            "pledge_signature": self.pledge_signature,
            "blog_url": self.blog_url,
            "metadata": self.metadata,
        }


class NegativeEscrowManager:
    """Manages negative balances, reverse reward escrows, and penalty clearing."""

    USD_TO_COIN_RATE = Decimal("1.25")
    REDEMPTION_RATE = Decimal("0.72")

    def __init__(self):
        """Initialize in-memory ledger storage."""
        self.records: Dict[str, DebitRecord] = {}
        self.user_balances: Dict[str, Decimal] = {}

    @classmethod
    def calculate_reverse_coins(cls, amount_usd: Decimal) -> Decimal:
        """Calculate required coins for reverse bounty under REWARD_POLICY rules.

        Args:
            amount_usd: Reverse bounty nominal USD value.

        Returns:
            Calculated platform coins as a positive Decimal requirement.
        """
        usd_clean = Decimal(str(amount_usd)).copy_abs()
        return (usd_clean * cls.USD_TO_COIN_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def record_debit(
        self,
        user_id: str,
        issue_id: int,
        amount_usd: Decimal,
        source_url: str = "",
        metadata: Dict[str, Any] = None
    ) -> DebitRecord:
        """Register a reverse bounty debit against an account.

        Args:
            user_id: Account identifier of the claiming agent.
            issue_id: Target GitHub issue ID.
            amount_usd: Negative bounty obligation in USD.
            source_url: External origin repository issue URL.
            metadata: Supplemental contextual information.

        Returns:
            Created DebitRecord instance.
        """
        coins = self.calculate_reverse_coins(amount_usd)
        now = time.time()
        record_id = f"deb_{hashlib.sha256(f'{user_id}:{issue_id}:{now}'.encode('utf-8')).hexdigest()[:16]}"

        record = DebitRecord(
            record_id=record_id,
            user_id=user_id,
            issue_id=issue_id,
            source_url=source_url,
            amount_usd=Decimal(str(amount_usd)).copy_abs(),
            coins_amount=coins,
            status=DebitStatus.PENDING,
            created_at=now,
            metadata=metadata or {},
        )

        self.records[record_id] = record
        current_balance = self.user_balances.get(user_id, Decimal("0.00"))
        self.user_balances[user_id] = current_balance - coins
        return record

    def settle_onchain(self, record_id: str, tx_id: str) -> DebitRecord:
        """Mark reverse debit as settled via on-chain transaction.

        Args:
            record_id: Identifier of the debit record.
            tx_id: Transaction ID / hash of the cryptocurrency transfer.

        Returns:
            Updated DebitRecord instance.
        """
        if record_id not in self.records:
            raise KeyError(f"Debit record not found: {record_id}")

        record = self.records[record_id]
        record.status = DebitStatus.SETTLED_ONCHAIN
        record.settled_at = time.time()
        record.tx_id = tx_id

        prior_bal = self.user_balances.get(record.user_id, Decimal("0.00"))
        self.user_balances[record.user_id] = prior_bal + record.coins_amount
        return record

    def waive_with_pledge_and_blog(
        self,
        record_id: str,
        pledge_signature: str,
        blog_url: str
    ) -> DebitRecord:
        """Waive reverse debit penalty upon submission of pledge and blog post.

        Args:
            record_id: Identifier of the debit record.
            pledge_signature: Cryptographic signature of anti-spam pledge.
            blog_url: Published post-mortem URL.

        Returns:
            Updated DebitRecord instance with waived status.
        """
        if record_id not in self.records:
            raise KeyError(f"Debit record not found: {record_id}")

        record = self.records[record_id]
        record.status = DebitStatus.WAIVED_VIA_PLEDGE
        record.settled_at = time.time()
        record.pledge_signature = pledge_signature
        record.blog_url = blog_url

        prior_bal = self.user_balances.get(record.user_id, Decimal("0.00"))
        self.user_balances[record.user_id] = prior_bal + record.coins_amount
        return record

    def get_user_balance(self, user_id: str) -> Decimal:
        """Get net platform coin balance for user."""
        return self.user_balances.get(user_id, Decimal("0.00"))
