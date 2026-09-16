"""Data models and type definitions for Boxy SaaS multi-tenant infrastructure."""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional


class TenantTier(str, Enum):
    """Subscription tiers supported by Boxy SaaS."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class TenantStatus(str, Enum):
    """Operational lifecycle statuses of a tenant."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"


class InvoiceStatus(str, Enum):
    """Settlement status for Bitcoin and fiat invoices."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ToolPermission(str, Enum):
    """Granular permissions granted to Boxy tool invocations."""

    READ_REPO = "read_repo"
    WRITE_REPO = "write_repo"
    SAVE_STICKY = "save_sticky"
    POST_COMMENT = "post_comment"
    LABEL_ISSUE = "label_issue"
    REVIEW_PR = "review_pr"
    RUN_COMMAND = "run_command"


@dataclass
class TierPolicy:
    """Resource quotas and pricing for a subscription tier."""

    tier: TenantTier
    max_monthly_tokens: int
    max_reviews_per_day: int
    max_concurrent_containers: int
    max_sticky_notes: int
    price_usd: Decimal
    price_btc: Decimal


@dataclass
class ApiKeyRecord:
    """Hashed representation of an API credential."""

    key_hash: str
    prefix: str
    tenant_id: str
    name: str
    created_at: float
    expires_at: Optional[float] = None
    revoked: bool = False


@dataclass
class Tenant:
    """Multi-tenant organization account entity."""

    tenant_id: str
    org_name: str
    tier: TenantTier
    status: TenantStatus
    contact_email: str
    created_at: float
    max_monthly_tokens: int
    max_reviews_per_day: int
    max_concurrent_containers: int
    max_sticky_notes: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StickyNote:
    """Isolated sticky note memory item associated with a tenant repository."""

    note_id: str
    tenant_id: str
    repo_full_name: str
    title: str
    content: str
    author: str
    created_at: float
    tags: List[str] = field(default_factory=list)


@dataclass
class UsageRecord:
    """Aggregated token and resource utilization record for a billing period."""

    tenant_id: str
    period: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    reviews_count: int = 0
    containers_spawned: int = 0

    @property
    def total_tokens(self) -> int:
        """Calculate aggregate tokens consumed across input, output, and cached."""
        return self.input_tokens + self.output_tokens + self.cached_tokens


@dataclass
class BitcoinInvoice:
    """Cryptographic invoice for Bitcoin settlement."""

    invoice_id: str
    tenant_id: str
    amount_usd: Decimal
    amount_btc: Decimal
    amount_satoshis: int
    address: str
    bip21_uri: str
    status: InvoiceStatus
    created_at: float
    expires_at: float
    txid: Optional[str] = None
    confirmations: int = 0


@dataclass
class BountySettlement:
    """Settlement calculation following official REWARD_POLICY formulas."""

    total_bounty_usd: Decimal
    coin_reward: Decimal
    contributor_ratio: Decimal
    contributor_coins: Decimal
    cash_payout_usd: Decimal
    platform_fee_usd: Decimal
    btc_rate_usd: Decimal
    btc_payout: Decimal
    payout_evm_address: str
    payout_stellar_address: str


@dataclass
class WebhookDelivery:
    """Normalized representation of a GitHub webhook payload."""

    event_type: str
    delivery_id: str
    installation_id: Optional[int]
    repository_full_name: str
    sender_login: str
    action: str
    payload: Dict[str, Any]
