"""Multi-tenant SaaS workspace manager and financial escrow calculator for OmniBlocks."""

import time
from decimal import Decimal
from typing import Dict, Optional
from packages.omni_sass.models import (
    EscrowCalculation,
    OmniProject,
    TenantRecord,
    WorkspaceMode,
)


class OmniSaasManager:
    """Manages cloud workspace tenants, project quotas, and bounty escrow calculations."""

    TIER_LIMITS = {
        "free": {"max_projects": 3, "max_storage_bytes": 100 * 1024 * 1024},
        "pro": {"max_projects": 50, "max_storage_bytes": 10 * 1024 * 1024 * 1024},
        "enterprise": {"max_projects": 10000, "max_storage_bytes": 1024 * 1024 * 1024 * 1024},
    }

    def __init__(self, initial_mode: WorkspaceMode = WorkspaceMode.STANDALONE) -> None:
        """Initialize workspace manager with default mode and empty tenant registry."""
        self.current_mode = initial_mode
        self.tenants: Dict[str, TenantRecord] = {}
        self.cloud_variables: Dict[str, Dict[str, str]] = {}

    def switch_mode(self, new_mode: WorkspaceMode) -> None:
        """Transition workspace operational mode."""
        self.current_mode = new_mode

    def create_tenant(
        self,
        tenant_id: str,
        organization_name: str,
        tier: str = "free",
    ) -> TenantRecord:
        """Create a new tenant record with tier quotas."""
        clean_tier = tier.lower()
        limits = self.TIER_LIMITS.get(clean_tier, self.TIER_LIMITS["free"])
        record = TenantRecord(
            tenant_id=tenant_id,
            organization_name=organization_name,
            tier=clean_tier,
            max_projects=limits["max_projects"],
            max_storage_bytes=limits["max_storage_bytes"],
        )
        self.tenants[tenant_id] = record
        return record

    def add_project(
        self,
        tenant_id: str,
        project_id: str,
        title: str,
        size_bytes: int,
    ) -> OmniProject:
        """Add a new project to a tenant, validating storage and project count limits."""
        if self.current_mode == WorkspaceMode.STANDALONE:
            project = OmniProject(
                project_id=project_id,
                tenant_id="local",
                title=title,
                size_bytes=size_bytes,
                created_at=time.time(),
            )
            return project

        if tenant_id not in self.tenants:
            raise KeyError(f"Tenant does not exist: {tenant_id}")

        tenant = self.tenants[tenant_id]
        if len(tenant.projects) >= tenant.max_projects:
            raise ValueError(f"Tenant project quota exceeded. Limit: {tenant.max_projects}")

        if tenant.current_storage_bytes + size_bytes > tenant.max_storage_bytes:
            raise ValueError("Tenant storage capacity exceeded.")

        project = OmniProject(
            project_id=project_id,
            tenant_id=tenant_id,
            title=title,
            size_bytes=size_bytes,
            created_at=time.time(),
        )
        tenant.projects[project_id] = project
        tenant.current_storage_bytes += size_bytes
        return project

    def delete_project(self, tenant_id: str, project_id: str) -> None:
        """Delete a project and reclaim tenant storage and project quotas."""
        if self.current_mode == WorkspaceMode.STANDALONE:
            return

        if tenant_id in self.tenants:
            tenant = self.tenants[tenant_id]
            if project_id in tenant.projects:
                freed_bytes = tenant.projects[project_id].size_bytes
                del tenant.projects[project_id]
                tenant.current_storage_bytes = max(0, tenant.current_storage_bytes - freed_bytes)

    def set_cloud_variable(self, tenant_id: str, project_id: str, name: str, value: str) -> None:
        """Store a cloud variable with tenant-level isolation."""
        is_standalone = self.current_mode == WorkspaceMode.STANDALONE
        scope_key = "standalone" if is_standalone else f"{tenant_id}:{project_id}"
        if scope_key not in self.cloud_variables:
            self.cloud_variables[scope_key] = {}
        self.cloud_variables[scope_key][name] = str(value)

    def get_cloud_variable(self, tenant_id: str, project_id: str, name: str) -> Optional[str]:
        """Retrieve a cloud variable within tenant scope."""
        is_standalone = self.current_mode == WorkspaceMode.STANDALONE
        scope_key = "standalone" if is_standalone else f"{tenant_id}:{project_id}"
        return self.cloud_variables.get(scope_key, {}).get(name)

    def calculate_bounty_escrow(self, bounty_usd: float = 9828150.0) -> EscrowCalculation:
        """Calculate coin and cash settlement following official REWARD_POLICY formulas."""
        dec_bounty = Decimal(str(bounty_usd))
        dec_coin_rate = Decimal("1.25")
        dec_cash_rate = Decimal("0.72")

        if dec_bounty < Decimal("50"):
            ratio = Decimal("0.95")
        elif dec_bounty < Decimal("200"):
            ratio = Decimal("0.92")
        elif dec_bounty < Decimal("500"):
            ratio = Decimal("0.90")
        elif dec_bounty < Decimal("1000"):
            ratio = Decimal("0.87")
        else:
            ratio = Decimal("0.85")

        coin_reward = dec_bounty * dec_coin_rate
        contributor_coins = coin_reward * ratio
        cash_payout = contributor_coins * dec_cash_rate
        platform_fee = dec_bounty - cash_payout

        return EscrowCalculation(
            bounty_usd=dec_bounty,
            coin_reward=coin_reward,
            contributor_ratio=ratio,
            contributor_coins=contributor_coins,
            cash_payout_usd=cash_payout,
            platform_fee_usd=platform_fee,
            exchange_rate_coin_to_usd=dec_cash_rate,
            exchange_rate_usd_to_coin=dec_coin_rate,
        )
