"""Tenant lifecycle manager, subscription policy enforcement, and credential binding."""

import time
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from packages.omni_boxy_saas.models import (
    ApiKeyRecord,
    Tenant,
    TenantStatus,
    TenantTier,
    TierPolicy,
)
from packages.omni_boxy_saas.security import generate_api_key, hash_api_key


TIER_POLICIES: Dict[TenantTier, TierPolicy] = {
    TenantTier.FREE: TierPolicy(
        tier=TenantTier.FREE,
        max_monthly_tokens=500_000,
        max_reviews_per_day=10,
        max_concurrent_containers=1,
        max_sticky_notes=50,
        price_usd=Decimal("0.00"),
        price_btc=Decimal("0.00000000"),
    ),
    TenantTier.PRO: TierPolicy(
        tier=TenantTier.PRO,
        max_monthly_tokens=10_000_000,
        max_reviews_per_day=200,
        max_concurrent_containers=5,
        max_sticky_notes=1_000,
        price_usd=Decimal("49.00"),
        price_btc=Decimal("0.00075000"),
    ),
    TenantTier.ENTERPRISE: TierPolicy(
        tier=TenantTier.ENTERPRISE,
        max_monthly_tokens=100_000_000,
        max_reviews_per_day=5_000,
        max_concurrent_containers=25,
        max_sticky_notes=100_000,
        price_usd=Decimal("499.00"),
        price_btc=Decimal("0.00750000"),
    ),
}


class TenantManager:
    """Coordinates tenant registration, quota allocation, and API key authentication."""

    def __init__(self) -> None:
        """Initialize in-memory tenant, credential, and repository mapping registers."""
        self._tenants: Dict[str, Tenant] = {}
        self._api_keys: Dict[str, ApiKeyRecord] = {}
        self._repo_to_tenant: Dict[str, str] = {}

    def create_tenant(
        self,
        tenant_id: str,
        org_name: str,
        tier: TenantTier = TenantTier.FREE,
        contact_email: str = "",
        status: TenantStatus = TenantStatus.ACTIVE,
    ) -> Tenant:
        """Register a new organization tenant with quotas resolved from tier policy."""
        if tenant_id in self._tenants:
            raise ValueError(f"Tenant ID '{tenant_id}' already exists")

        policy = TIER_POLICIES.get(tier, TIER_POLICIES[TenantTier.FREE])
        tenant = Tenant(
            tenant_id=tenant_id,
            org_name=org_name,
            tier=tier,
            status=status,
            contact_email=contact_email,
            created_at=time.time(),
            max_monthly_tokens=policy.max_monthly_tokens,
            max_reviews_per_day=policy.max_reviews_per_day,
            max_concurrent_containers=policy.max_concurrent_containers,
            max_sticky_notes=policy.max_sticky_notes,
        )
        self._tenants[tenant_id] = tenant
        return tenant

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Retrieve tenant profile by unique identifier."""
        return self._tenants.get(tenant_id)

    def list_tenants(self) -> List[Tenant]:
        """Enumerate all registered tenant profiles."""
        tenants_list = list(self._tenants.values())
        return tenants_list

    def update_tier(self, tenant_id: str, new_tier: TenantTier) -> Tenant:
        """Update subscription tier and dynamically recalculate resource ceilings."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise KeyError(f"Tenant '{tenant_id}' not found")

        policy = TIER_POLICIES.get(new_tier, TIER_POLICIES[TenantTier.FREE])
        tenant.tier = new_tier
        tenant.max_monthly_tokens = policy.max_monthly_tokens
        tenant.max_reviews_per_day = policy.max_reviews_per_day
        tenant.max_concurrent_containers = policy.max_concurrent_containers
        tenant.max_sticky_notes = policy.max_sticky_notes
        return tenant

    def update_status(self, tenant_id: str, new_status: TenantStatus) -> Tenant:
        """Transition tenant operational status."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise KeyError(f"Tenant '{tenant_id}' not found")
        tenant.status = new_status
        return tenant

    def issue_api_key(
        self,
        tenant_id: str,
        name: str = "default",
        expires_in_seconds: Optional[float] = None,
    ) -> Tuple[str, ApiKeyRecord]:
        """Issue high-entropy API key bound to tenant and store hashed record."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise KeyError(f"Tenant '{tenant_id}' not found")

        raw_key, key_hash, prefix = generate_api_key(tenant_id)
        now = time.time()
        expires_at = now + expires_in_seconds if expires_in_seconds else None

        record = ApiKeyRecord(
            key_hash=key_hash,
            prefix=prefix,
            tenant_id=tenant_id,
            name=name,
            created_at=now,
            expires_at=expires_at,
            revoked=False,
        )
        self._api_keys[key_hash] = record
        result = (raw_key, record)
        return result

    def revoke_api_key(self, raw_or_hashed_key: str) -> bool:
        """Revoke active API credential by raw token or pre-hashed identifier."""
        target_hash = (
            hash_api_key(raw_or_hashed_key)
            if raw_or_hashed_key.startswith("boxy_")
            else raw_or_hashed_key
        )
        if target_hash in self._api_keys:
            self._api_keys[target_hash].revoked = True
            return True
        return False

    def authenticate_key(self, raw_key: str) -> Optional[Tenant]:
        """Authenticate caller via bearer key, verifying active status and expiry."""
        if not raw_key:
            return None
        key_hash = hash_api_key(raw_key)
        record = self._api_keys.get(key_hash)
        if not record or record.revoked:
            return None

        if record.expires_at and time.time() > record.expires_at:
            return None

        tenant = self.get_tenant(record.tenant_id)
        if not tenant or tenant.status != TenantStatus.ACTIVE:
            return None

        return tenant

    def map_repository(self, repo_full_name: str, tenant_id: str) -> None:
        """Associate GitHub repository full name with responsible tenant account."""
        if tenant_id not in self._tenants:
            raise KeyError(f"Tenant '{tenant_id}' does not exist")
        normalized = repo_full_name.lower().strip()
        self._repo_to_tenant[normalized] = tenant_id

    def get_tenant_for_repo(self, repo_full_name: str) -> Optional[Tenant]:
        """Resolve owner tenant associated with GitHub repository."""
        normalized = repo_full_name.lower().strip()
        tenant_id = self._repo_to_tenant.get(normalized)
        if not tenant_id:
            return None
        return self.get_tenant(tenant_id)

    def delete_tenant(self, tenant_id: str) -> bool:
        """Remove tenant record, invalidating associated API credentials and mappings."""
        if tenant_id not in self._tenants:
            return False

        del self._tenants[tenant_id]

        keys_to_remove = [k for k, v in self._api_keys.items() if v.tenant_id == tenant_id]
        for key_hash in keys_to_remove:
            del self._api_keys[key_hash]

        repos_to_remove = [repo for repo, t_id in self._repo_to_tenant.items() if t_id == tenant_id]
        for repo in repos_to_remove:
            del self._repo_to_tenant[repo]

        return True
