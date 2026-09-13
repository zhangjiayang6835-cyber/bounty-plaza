"""Multi-tenant isolation, quota enforcement, and RBAC management engine."""

import hashlib
import hmac
import json
import time
import uuid
from typing import Any

from packages.saas_mode.models import (
    AuditEntry,
    DEFAULT_TIER_LIMITS,
    ExecutionMode,
    FeatureNotAllowedError,
    Permission,
    QuotaExceededError,
    QuotaUsage,
    Role,
    Tenant,
    TenantEvent,
    TenantNotFoundError,
    TenantStatus,
    TenantSuspendedError,
    TenantTier,
    TierLimits,
    UnauthorizedAccessError,
    User,
)


ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.OWNER: {
        Permission.PROJECT_CREATE,
        Permission.PROJECT_READ,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_DELETE,
        Permission.TENANT_MANAGE,
        Permission.BILLING_READ,
        Permission.BILLING_WRITE,
        Permission.AUDIT_READ,
    },
    Role.ADMIN: {
        Permission.PROJECT_CREATE,
        Permission.PROJECT_READ,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_DELETE,
        Permission.TENANT_MANAGE,
        Permission.BILLING_READ,
        Permission.AUDIT_READ,
    },
    Role.BILLING_MANAGER: {
        Permission.PROJECT_READ,
        Permission.BILLING_READ,
        Permission.BILLING_WRITE,
        Permission.AUDIT_READ,
    },
    Role.MEMBER: {
        Permission.PROJECT_CREATE,
        Permission.PROJECT_READ,
        Permission.PROJECT_UPDATE,
    },
    Role.VIEWER: {
        Permission.PROJECT_READ,
    },
}


class MultiTenantStore:
    """In-memory partitioned storage implementing tenant logical isolation."""

    def __init__(self) -> None:
        """Initialize empty tenant, user, and project partitions."""
        self._tenants: dict[str, Tenant] = {}
        self._users: dict[str, User] = {}
        self._projects: dict[str, dict[str, dict[str, Any]]] = {}

    def add_tenant(self, tenant: Tenant) -> None:
        """Register a new tenant organization."""
        self._tenants[tenant.tenant_id] = tenant
        if tenant.tenant_id not in self._projects:
            self._projects[tenant.tenant_id] = {}

    def get_tenant(self, tenant_id: str) -> Tenant:
        """Retrieve tenant metadata or raise TenantNotFoundError."""
        if tenant_id not in self._tenants:
            msg = f"Tenant {tenant_id} not registered"
            raise TenantNotFoundError(msg)
        return self._tenants[tenant_id]

    def has_tenant(self, tenant_id: str) -> bool:
        """Check if tenant exists in store."""
        return tenant_id in self._tenants

    def update_tenant_status(self, tenant_id: str, status: TenantStatus) -> None:
        """Update operational status for target tenant."""
        tenant = self.get_tenant(tenant_id)
        tenant.status = status

    def update_tenant_tier(self, tenant_id: str, tier: TenantTier) -> None:
        """Update subscription tier for target tenant."""
        tenant = self.get_tenant(tenant_id)
        tenant.tier = tier

    def add_user(self, user: User) -> None:
        """Register a user within their assigned tenant."""
        self._users[user.user_id] = user

    def get_user(self, user_id: str) -> User:
        """Retrieve user record or raise UnauthorizedAccessError."""
        if user_id not in self._users:
            msg = f"User {user_id} not found"
            raise UnauthorizedAccessError(msg)
        return self._users[user_id]

    def get_tenant_users(self, tenant_id: str) -> list[User]:
        """List all users assigned to target tenant."""
        user_list = [u for u in self._users.values() if u.tenant_id == tenant_id]
        return user_list

    def save_project(self, tenant_id: str, project_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Save a project document partitioned strictly by tenant identifier."""
        if tenant_id not in self._projects:
            self._projects[tenant_id] = {}
        self._projects[tenant_id][project_id] = data
        return data

    def get_project(self, tenant_id: str, project_id: str) -> dict[str, Any]:
        """Fetch project ensuring cross-tenant boundaries are enforced."""
        tenant_projects = self._projects.get(tenant_id, {})
        if project_id not in tenant_projects:
            msg = f"Project {project_id} not found for tenant {tenant_id}"
            raise KeyError(msg)
        return tenant_projects[project_id]

    def list_projects(self, tenant_id: str) -> list[dict[str, Any]]:
        """List all projects belonging to a single tenant."""
        items = list(self._projects.get(tenant_id, {}).values())
        return items

    def delete_project(self, tenant_id: str, project_id: str) -> bool:
        """Delete project from target tenant partition."""
        tenant_projects = self._projects.get(tenant_id, {})
        if project_id in tenant_projects:
            del tenant_projects[project_id]
            return True
        return False


class RBACManager:
    """Evaluates role-based access control policies."""

    @staticmethod
    def has_permission(role: Role, permission: Permission) -> bool:
        """Check if role grants requested permission."""
        permitted = ROLE_PERMISSIONS.get(role, set())
        return permission in permitted

    @staticmethod
    def validate_access(user: User, permission: Permission) -> None:
        """Verify active user status and permission grant."""
        if not user.is_active:
            msg = f"User {user.user_id} is inactive"
            raise UnauthorizedAccessError(msg)
        if not RBACManager.has_permission(user.role, permission):
            msg = f"User {user.user_id} with role {user.role.value} lacks {permission.value}"
            raise UnauthorizedAccessError(msg)


class QuotaManager:
    """Tracks and enforces resource quotas across tiers."""

    def __init__(self, limits_map: dict[TenantTier, TierLimits] | None = None) -> None:
        """Initialize quota tracker with default or custom tier limits."""
        self._limits = limits_map if limits_map is not None else DEFAULT_TIER_LIMITS
        self._usages: dict[str, QuotaUsage] = {}

    def get_limits(self, tier: TenantTier) -> TierLimits:
        """Retrieve resource limits for target tier."""
        return self._limits[tier]

    def get_usage(self, tenant_id: str) -> QuotaUsage:
        """Retrieve current usage counters or initialize new tracker."""
        if tenant_id not in self._usages:
            self._usages[tenant_id] = QuotaUsage(tenant_id=tenant_id)
        return self._usages[tenant_id]

    def check_project_limit(self, tenant: Tenant) -> None:
        """Verify project count does not breach tier allocation."""
        limits = self.get_limits(tenant.tier)
        usage = self.get_usage(tenant.tenant_id)
        if usage.project_count >= limits.max_projects:
            msg = f"Project limit {limits.max_projects} exceeded for tier {tenant.tier.value}"
            raise QuotaExceededError(msg)

    def check_storage_limit(self, tenant: Tenant, additional_bytes: int) -> None:
        """Verify storage expansion does not breach tier allocation."""
        limits = self.get_limits(tenant.tier)
        usage = self.get_usage(tenant.tenant_id)
        if usage.storage_bytes + additional_bytes > limits.max_storage_bytes:
            msg = f"Storage limit {limits.max_storage_bytes} bytes exceeded"
            raise QuotaExceededError(msg)

    def check_api_request_limit(self, tenant: Tenant) -> None:
        """Verify per-minute API request rate does not breach tier allocation."""
        limits = self.get_limits(tenant.tier)
        usage = self.get_usage(tenant.tenant_id)
        if usage.api_requests_count >= limits.max_api_requests_per_minute:
            msg = f"API rate limit {limits.max_api_requests_per_minute} req/min exceeded"
            raise QuotaExceededError(msg)

    def verify_feature(self, tenant: Tenant, feature_key: str) -> None:
        """Validate if advanced feature is unlocked for tier."""
        limits = self.get_limits(tenant.tier)
        if feature_key == "webhooks" and not limits.allows_webhooks:
            msg = f"Feature webhooks not allowed on tier {tenant.tier.value}"
            raise FeatureNotAllowedError(msg)
        if feature_key == "custom_domains" and not limits.allows_custom_domains:
            msg = f"Feature custom_domains not allowed on tier {tenant.tier.value}"
            raise FeatureNotAllowedError(msg)

    def increment_projects(self, tenant_id: str, count: int = 1) -> None:
        """Increment active project count."""
        usage = self.get_usage(tenant_id)
        usage.project_count += count

    def decrement_projects(self, tenant_id: str, count: int = 1) -> None:
        """Decrement active project count safely."""
        usage = self.get_usage(tenant_id)
        usage.project_count = max(0, usage.project_count - count)

    def increment_storage(self, tenant_id: str, byte_count: int) -> None:
        """Add consumed storage bytes."""
        usage = self.get_usage(tenant_id)
        usage.storage_bytes += byte_count

    def decrement_storage(self, tenant_id: str, byte_count: int) -> None:
        """Subtract freed storage bytes."""
        usage = self.get_usage(tenant_id)
        usage.storage_bytes = max(0, usage.storage_bytes - byte_count)

    def record_api_request(self, tenant_id: str) -> None:
        """Log single API invocation."""
        usage = self.get_usage(tenant_id)
        usage.api_requests_count += 1

    def reset_api_request_window(self, tenant_id: str) -> None:
        """Reset rate limit sliding window counter."""
        usage = self.get_usage(tenant_id)
        usage.api_requests_count = 0


class WebhookDispatcher:
    """Dispatches cryptographic tenant lifecycle webhooks."""

    @staticmethod
    def sign_payload(payload_bytes: bytes, secret: str) -> str:
        """Generate HMAC-SHA256 signature for webhook payload."""
        key = secret.encode("utf-8")
        mac = hmac.new(key, payload_bytes, hashlib.sha256)
        digest_hex = mac.hexdigest()
        return digest_hex

    @staticmethod
    def verify_signature(payload_bytes: bytes, secret: str, signature: str) -> bool:
        """Verify webhook signature using constant-time comparison."""
        expected = WebhookDispatcher.sign_payload(payload_bytes, secret)
        valid = hmac.compare_digest(expected, signature)
        return valid

    @staticmethod
    def construct_event(tenant_id: str, event_type: str, payload: dict[str, Any]) -> TenantEvent:
        """Construct a standardized tenant event."""
        event_obj = TenantEvent(
            event_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            event_type=event_type,
            payload=payload,
            timestamp=time.time(),
        )
        return event_obj


class AuditLogger:
    """Append-only audit trail logger."""

    def __init__(self) -> None:
        """Initialize empty audit entries index."""
        self._entries: list[AuditEntry] = []

    def record(
        self,
        tenant_id: str,
        actor_id: str,
        action: str,
        target: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEntry:
        """Record an immutable audit event."""
        entry = AuditEntry(
            entry_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=action,
            target=target,
            timestamp=time.time(),
            metadata=metadata if metadata is not None else {},
        )
        self._entries.append(entry)
        return entry

    def get_tenant_entries(self, tenant_id: str) -> list[AuditEntry]:
        """Filter audit trail by tenant identifier."""
        matched = [e for e in self._entries if e.tenant_id == tenant_id]
        return matched


class SaaSModeManager:
    """Master coordinator managing execution mode, multi-tenancy, and governance."""

    def __init__(self, mode: ExecutionMode = ExecutionMode.SAAS) -> None:
        """Initialize SaaS manager with store, quota, RBAC, and audit modules."""
        self._mode = mode
        self._store = MultiTenantStore()
        self._quota = QuotaManager()
        self._rbac = RBACManager()
        self._webhook = WebhookDispatcher()
        self._audit = AuditLogger()

    @property
    def mode(self) -> ExecutionMode:
        """Return active execution mode."""
        return self._mode

    def set_mode(self, mode: ExecutionMode) -> None:
        """Switch execution mode between STANDALONE and SAAS."""
        self._mode = mode

    def is_saas_mode(self) -> bool:
        """Return true if running in multi-tenant SaaS mode."""
        return self._mode == ExecutionMode.SAAS

    def is_standalone_mode(self) -> bool:
        """Return true if running in standalone local mode."""
        return self._mode == ExecutionMode.STANDALONE

    def provision_tenant(
        self,
        name: str,
        owner_id: str,
        tier: TenantTier = TenantTier.FREE,
        metadata: dict[str, Any] | None = None,
    ) -> Tenant:
        """Provision a new tenant and bind initial owner user."""
        tenant_uuid = str(uuid.uuid4())
        tenant = Tenant(
            tenant_id=tenant_uuid,
            name=name,
            tier=tier,
            status=TenantStatus.ACTIVE,
            created_at=time.time(),
            owner_id=owner_id,
            metadata=metadata if metadata is not None else {},
        )
        self._store.add_tenant(tenant)

        owner_user = User(
            user_id=owner_id,
            tenant_id=tenant_uuid,
            role=Role.OWNER,
            email=f"{owner_id}@tenant.local",
            is_active=True,
        )
        self._store.add_user(owner_user)

        self._audit.record(
            tenant_id=tenant_uuid,
            actor_id=owner_id,
            action="tenant.provision",
            target=tenant_uuid,
            metadata={"tier": tier.value},
        )
        return tenant

    def add_tenant_user(
        self,
        actor_id: str,
        tenant_id: str,
        user_id: str,
        role: Role,
        email: str,
    ) -> User:
        """Add team member to tenant with RBAC validation."""
        if self.is_saas_mode():
            actor = self._store.get_user(actor_id)
            if actor.tenant_id != tenant_id:
                msg = f"Cross-tenant administration denied for actor {actor_id}"
                raise UnauthorizedAccessError(msg)
            self._rbac.validate_access(actor, Permission.TENANT_MANAGE)

        user = User(
            user_id=user_id,
            tenant_id=tenant_id,
            role=role,
            email=email,
            is_active=True,
        )
        self._store.add_user(user)

        self._audit.record(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="user.add",
            target=user_id,
            metadata={"role": role.value},
        )
        return user

    def create_project(
        self,
        user_id: str,
        project_id: str,
        initial_storage_bytes: int = 1024,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create project validating tenant status, RBAC permissions, and quota limits."""
        if self.is_standalone_mode():
            standalone_project = {
                "project_id": project_id,
                "tenant_id": "standalone_tenant",
                "storage_bytes": initial_storage_bytes,
                "created_at": time.time(),
                "metadata": metadata if metadata is not None else {},
            }
            return standalone_project

        user = self._store.get_user(user_id)
        self._rbac.validate_access(user, Permission.PROJECT_CREATE)

        tenant = self._store.get_tenant(user.tenant_id)
        if tenant.status != TenantStatus.ACTIVE and tenant.status != TenantStatus.TRIAL:
            msg = f"Tenant {tenant.tenant_id} is in non-operational state: {tenant.status.value}"
            raise TenantSuspendedError(msg)

        self._quota.check_project_limit(tenant)
        self._quota.check_storage_limit(tenant, initial_storage_bytes)

        project_record = {
            "project_id": project_id,
            "tenant_id": user.tenant_id,
            "storage_bytes": initial_storage_bytes,
            "created_at": time.time(),
            "created_by": user_id,
            "metadata": metadata if metadata is not None else {},
        }
        self._store.save_project(user.tenant_id, project_id, project_record)
        self._quota.increment_projects(user.tenant_id, 1)
        self._quota.increment_storage(user.tenant_id, initial_storage_bytes)

        self._audit.record(
            tenant_id=user.tenant_id,
            actor_id=user_id,
            action="project.create",
            target=project_id,
            metadata={"storage_bytes": initial_storage_bytes},
        )
        return project_record

    def get_project(self, user_id: str, project_id: str) -> dict[str, Any]:
        """Read project enforcing tenant boundary isolation."""
        if self.is_standalone_mode():
            res = {"project_id": project_id, "mode": "standalone"}
            return res

        user = self._store.get_user(user_id)
        self._rbac.validate_access(user, Permission.PROJECT_READ)
        project = self._store.get_project(user.tenant_id, project_id)
        return project

    def delete_project(
        self,
        user_id: str,
        project_id: str,
        freed_storage_bytes: int = 1024,
    ) -> bool:
        """Delete project releasing consumed tenant quota."""
        if self.is_standalone_mode():
            return True

        user = self._store.get_user(user_id)
        self._rbac.validate_access(user, Permission.PROJECT_DELETE)

        deleted = self._store.delete_project(user.tenant_id, project_id)
        if deleted:
            self._quota.decrement_projects(user.tenant_id, 1)
            self._quota.decrement_storage(user.tenant_id, freed_storage_bytes)
            self._audit.record(
                tenant_id=user.tenant_id,
                actor_id=user_id,
                action="project.delete",
                target=project_id,
                metadata={"freed_storage_bytes": freed_storage_bytes},
            )
        return deleted

    def upgrade_tier(
        self,
        actor_id: str,
        tenant_id: str,
        new_tier: TenantTier,
    ) -> Tenant:
        """Upgrade or downgrade tenant subscription tier."""
        if self.is_saas_mode():
            actor = self._store.get_user(actor_id)
            if actor.tenant_id != tenant_id:
                msg = f"Tenant boundary violation by actor {actor_id}"
                raise UnauthorizedAccessError(msg)
            self._rbac.validate_access(actor, Permission.BILLING_WRITE)

        self._store.update_tenant_tier(tenant_id, new_tier)
        tenant = self._store.get_tenant(tenant_id)

        self._audit.record(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="tenant.tier_change",
            target=tenant_id,
            metadata={"new_tier": new_tier.value},
        )
        return tenant

    def emit_webhook_event(
        self,
        tenant_id: str,
        event_type: str,
        payload: dict[str, Any],
        secret: str,
    ) -> tuple[TenantEvent, str]:
        """Create signed webhook event if tenant tier permits webhooks."""
        tenant = self._store.get_tenant(tenant_id)
        self._quota.verify_feature(tenant, "webhooks")

        event_obj = self._webhook.construct_event(tenant_id, event_type, payload)
        serialized = json.dumps(event_obj.payload, sort_keys=True).encode("utf-8")
        signature = self._webhook.sign_payload(serialized, secret)
        return event_obj, signature

    def get_tenant_summary(self, tenant_id: str) -> dict[str, Any]:
        """Summarize tenant tier, status, limits, and resource consumption."""
        tenant = self._store.get_tenant(tenant_id)
        limits = self._quota.get_limits(tenant.tier)
        usage = self._quota.get_usage(tenant_id)
        summary = {
            "tenant_id": tenant.tenant_id,
            "name": tenant.name,
            "tier": tenant.tier.value,
            "status": tenant.status.value,
            "limits": {
                "max_projects": limits.max_projects,
                "max_storage_bytes": limits.max_storage_bytes,
                "max_api_requests_per_minute": limits.max_api_requests_per_minute,
                "allows_webhooks": limits.allows_webhooks,
                "allows_custom_domains": limits.allows_custom_domains,
            },
            "usage": {
                "project_count": usage.project_count,
                "storage_bytes": usage.storage_bytes,
                "api_requests_count": usage.api_requests_count,
            },
        }
        return summary
