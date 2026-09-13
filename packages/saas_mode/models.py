"""Data models and custom exception definitions for SaaS mode."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExecutionMode(str, Enum):
    """Runtime execution mode for the application."""
    STANDALONE = "standalone"
    SAAS = "saas"


class TenantTier(str, Enum):
    """Subscription tier defining operational limits."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class TenantStatus(str, Enum):
    """Lifecycle status of a tenant account."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    QUOTA_EXCEEDED = "quota_exceeded"
    DEPROVISIONED = "deprovisioned"


class Role(str, Enum):
    """Role-based access control roles."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
    BILLING_MANAGER = "billing_manager"


class Permission(str, Enum):
    """Granular operational permissions."""
    PROJECT_CREATE = "project:create"
    PROJECT_READ = "project:read"
    PROJECT_UPDATE = "project:update"
    PROJECT_DELETE = "project:delete"
    TENANT_MANAGE = "tenant:manage"
    BILLING_READ = "billing:read"
    BILLING_WRITE = "billing:write"
    AUDIT_READ = "audit:read"


@dataclass(frozen=True)
class TierLimits:
    """Resource constraints allocated to a tier."""
    max_projects: int
    max_storage_bytes: int
    max_api_requests_per_minute: int
    max_concurrent_workers: int
    allows_custom_domains: bool
    allows_webhooks: bool


DEFAULT_TIER_LIMITS: dict[TenantTier, TierLimits] = {
    TenantTier.FREE: TierLimits(
        max_projects=3,
        max_storage_bytes=100 * 1024 * 1024,
        max_api_requests_per_minute=60,
        max_concurrent_workers=1,
        allows_custom_domains=False,
        allows_webhooks=False,
    ),
    TenantTier.PRO: TierLimits(
        max_projects=50,
        max_storage_bytes=10 * 1024 * 1024 * 1024,
        max_api_requests_per_minute=600,
        max_concurrent_workers=5,
        allows_custom_domains=True,
        allows_webhooks=True,
    ),
    TenantTier.ENTERPRISE: TierLimits(
        max_projects=10000,
        max_storage_bytes=1024 * 1024 * 1024 * 1024,
        max_api_requests_per_minute=10000,
        max_concurrent_workers=50,
        allows_custom_domains=True,
        allows_webhooks=True,
    ),
}


@dataclass
class Tenant:
    """Multi-tenant organization entity."""
    tenant_id: str
    name: str
    tier: TenantTier = TenantTier.FREE
    status: TenantStatus = TenantStatus.ACTIVE
    created_at: float = 0.0
    owner_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class User:
    """User associated with a specific tenant."""
    user_id: str
    tenant_id: str
    role: Role = Role.MEMBER
    email: str = ""
    is_active: bool = True


@dataclass
class QuotaUsage:
    """Resource consumption metrics for a tenant."""
    tenant_id: str
    project_count: int = 0
    storage_bytes: int = 0
    api_requests_count: int = 0
    concurrent_workers: int = 0


@dataclass
class TenantEvent:
    """Event triggered by tenant lifecycle or usage changes."""
    event_id: str
    tenant_id: str
    event_type: str
    payload: dict[str, Any]
    timestamp: float


@dataclass
class AuditEntry:
    """Immutable audit trail log record."""
    entry_id: str
    tenant_id: str
    actor_id: str
    action: str
    target: str
    timestamp: float
    metadata: dict[str, Any] = field(default_factory=dict)


class SaaSModeError(Exception):
    """Base exception for all SaaS mode operations."""


class QuotaExceededError(SaaSModeError):
    """Raised when an operation violates tenant tier quotas."""


class TenantNotFoundError(SaaSModeError):
    """Raised when the requested tenant does not exist."""


class TenantSuspendedError(SaaSModeError):
    """Raised when an operation is attempted on a suspended tenant."""


class UnauthorizedAccessError(SaaSModeError):
    """Raised when an actor lacks sufficient role permissions."""


class FeatureNotAllowedError(SaaSModeError):
    """Raised when a requested feature is disabled for the tenant tier."""
