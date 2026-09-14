"""Unit and integration tests validating Issue #1548 SaaS mode capabilities."""

import hashlib
import hmac
import json
import pytest

from packages.saas_mode.manager import (
    MultiTenantStore,
    QuotaManager,
    RBACManager,
    SaaSModeManager,
    WebhookDispatcher,
)
from packages.saas_mode.models import (
    ExecutionMode,
    FeatureNotAllowedError,
    Permission,
    QuotaExceededError,
    Role,
    Tenant,
    TenantStatus,
    TenantSuspendedError,
    TenantTier,
    UnauthorizedAccessError,
    User,
)
from packages.saas_mode.verifier import SaaSModeVerifier


def test_execution_mode_switching() -> None:
    """Test switching between standalone and multi-tenant SaaS modes."""
    mgr = SaaSModeManager(ExecutionMode.SAAS)
    assert mgr.is_saas_mode() is True
    assert mgr.is_standalone_mode() is False

    mgr.set_mode(ExecutionMode.STANDALONE)
    assert mgr.is_saas_mode() is False
    assert mgr.is_standalone_mode() is True


def test_tenant_provisioning_and_lookup() -> None:
    """Test tenant registration, owner user assignment, and retrieval."""
    mgr = SaaSModeManager(ExecutionMode.SAAS)
    tenant = mgr.provision_tenant("Acme Corp", "owner_acme", tier=TenantTier.PRO)

    assert tenant.name == "Acme Corp"
    assert tenant.tier == TenantTier.PRO
    assert tenant.status == TenantStatus.ACTIVE

    summary = mgr.get_tenant_summary(tenant.tenant_id)
    assert summary["name"] == "Acme Corp"
    assert summary["tier"] == "pro"
    assert summary["limits"]["max_projects"] == 50


def test_tenant_isolation_enforcement() -> None:
    """Test that projects created in Tenant A are invisible to Tenant B."""
    mgr = SaaSModeManager(ExecutionMode.SAAS)
    tenant_a = mgr.provision_tenant("Tenant A", "user_a")
    tenant_b = mgr.provision_tenant("Tenant B", "user_b")

    project = mgr.create_project("user_a", "proj_a", initial_storage_bytes=2048)
    assert project["project_id"] == "proj_a"
    assert project["tenant_id"] == tenant_a.tenant_id

    with pytest.raises(KeyError):
        mgr._store.get_project(tenant_b.tenant_id, "proj_a")


def test_quota_project_limit_enforcement() -> None:
    """Test that free tier caps project creation at 3 projects."""
    mgr = SaaSModeManager(ExecutionMode.SAAS)
    mgr.provision_tenant("Small Biz", "biz_owner", tier=TenantTier.FREE)

    mgr.create_project("biz_owner", "p1")
    mgr.create_project("biz_owner", "p2")
    mgr.create_project("biz_owner", "p3")

    with pytest.raises(QuotaExceededError) as exc_info:
        mgr.create_project("biz_owner", "p4")

    assert "Project limit 3 exceeded" in str(exc_info.value)


def test_quota_storage_limit_enforcement() -> None:
    """Test that allocating beyond tier storage capacity raises QuotaExceededError."""
    mgr = SaaSModeManager(ExecutionMode.SAAS)
    mgr.provision_tenant("Data Corp", "data_owner", tier=TenantTier.FREE)

    too_large = 101 * 1024 * 1024
    with pytest.raises(QuotaExceededError) as exc_info:
        mgr.create_project("data_owner", "p_giant", initial_storage_bytes=too_large)

    assert "Storage limit" in str(exc_info.value)


def test_quota_release_on_project_deletion() -> None:
    """Test that deleting a project releases allocated quota counters."""
    mgr = SaaSModeManager(ExecutionMode.SAAS)
    tenant = mgr.provision_tenant("Lifecycle Org", "life_owner", tier=TenantTier.FREE)

    mgr.create_project("life_owner", "temp_proj", initial_storage_bytes=5000)
    summary_before = mgr.get_tenant_summary(tenant.tenant_id)
    assert summary_before["usage"]["project_count"] == 1
    assert summary_before["usage"]["storage_bytes"] == 5000

    deleted = mgr.delete_project("life_owner", "temp_proj", freed_storage_bytes=5000)
    assert deleted is True

    summary_after = mgr.get_tenant_summary(tenant.tenant_id)
    assert summary_after["usage"]["project_count"] == 0
    assert summary_after["usage"]["storage_bytes"] == 0


def test_tier_upgrade_and_quota_expansion() -> None:
    """Test that upgrading from Free to Pro unlocks higher limits."""
    mgr = SaaSModeManager(ExecutionMode.SAAS)
    tenant = mgr.provision_tenant("Growth Co", "growth_owner", tier=TenantTier.FREE)

    mgr.create_project("growth_owner", "p1")
    mgr.create_project("growth_owner", "p2")
    mgr.create_project("growth_owner", "p3")

    with pytest.raises(QuotaExceededError):
        mgr.create_project("growth_owner", "p4")

    mgr.upgrade_tier("growth_owner", tenant.tenant_id, TenantTier.PRO)
    upgraded_proj = mgr.create_project("growth_owner", "p4")
    assert upgraded_proj["project_id"] == "p4"

    summary = mgr.get_tenant_summary(tenant.tenant_id)
    assert summary["tier"] == "pro"
    assert summary["limits"]["max_projects"] == 50


def test_rbac_owner_and_admin_permissions() -> None:
    """Test permission grants for owner and admin roles."""
    assert RBACManager.has_permission(Role.OWNER, Permission.PROJECT_CREATE) is True
    assert RBACManager.has_permission(Role.OWNER, Permission.BILLING_WRITE) is True
    assert RBACManager.has_permission(Role.ADMIN, Permission.PROJECT_CREATE) is True
    assert RBACManager.has_permission(Role.ADMIN, Permission.BILLING_WRITE) is False


def test_rbac_member_and_viewer_restrictions() -> None:
    """Test that viewer cannot create projects and member cannot manage tenants."""
    mgr = SaaSModeManager(ExecutionMode.SAAS)
    tenant = mgr.provision_tenant("Studio", "studio_owner")

    mgr.add_tenant_user("studio_owner", tenant.tenant_id, "viewer1", Role.VIEWER, "v1@studio.local")
    mgr.add_tenant_user("studio_owner", tenant.tenant_id, "member1", Role.MEMBER, "m1@studio.local")

    with pytest.raises(UnauthorizedAccessError):
        mgr.create_project("viewer1", "viewer_proj")

    with pytest.raises(UnauthorizedAccessError):
        mgr.add_tenant_user("member1", tenant.tenant_id, "user2", Role.VIEWER, "u2@studio.local")


def test_inactive_user_rejection() -> None:
    """Test that deactivated users cannot perform actions."""
    mgr = SaaSModeManager(ExecutionMode.SAAS)
    tenant = mgr.provision_tenant("Sec Corp", "sec_owner")
    user = mgr.add_tenant_user("sec_owner", tenant.tenant_id, "sec_member", Role.MEMBER, "m@sec.local")
    user.is_active = False

    with pytest.raises(UnauthorizedAccessError) as exc_info:
        mgr.create_project("sec_member", "inactive_p")

    assert "inactive" in str(exc_info.value)


def test_suspended_tenant_rejection() -> None:
    """Test that operations are blocked when tenant status is suspended."""
    mgr = SaaSModeManager(ExecutionMode.SAAS)
    tenant = mgr.provision_tenant("Blocked Org", "block_owner")
    tenant.status = TenantStatus.SUSPENDED

    with pytest.raises(TenantSuspendedError):
        mgr.create_project("block_owner", "blocked_proj")


def test_trial_tenant_operational() -> None:
    """Test that trial tenants are allowed to create projects."""
    mgr = SaaSModeManager(ExecutionMode.SAAS)
    tenant = mgr.provision_tenant("Trial Org", "trial_owner")
    tenant.status = TenantStatus.TRIAL

    proj = mgr.create_project("trial_owner", "trial_proj")
    assert proj["project_id"] == "trial_proj"


def test_feature_gating_webhooks() -> None:
    """Test that webhook dispatch is blocked on free tier and allowed on pro."""
    mgr = SaaSModeManager(ExecutionMode.SAAS)
    free_tenant = mgr.provision_tenant("Free Org", "free_user", tier=TenantTier.FREE)
    pro_tenant = mgr.provision_tenant("Pro Org", "pro_user", tier=TenantTier.PRO)

    with pytest.raises(FeatureNotAllowedError):
        mgr.emit_webhook_event(free_tenant.tenant_id, "event.test", {}, "secret")

    event_obj, sig = mgr.emit_webhook_event(
        pro_tenant.tenant_id, "event.test", {"status": "ok"}, "secret"
    )
    assert event_obj.event_type == "event.test"
    assert len(sig) == 64


def test_webhook_hmac_sha256_cryptographic_verification() -> None:
    """Test HMAC-SHA256 signature verification for webhook payloads."""
    secret = "production_webhook_secret_key_888"
    payload = json.dumps({"event": "billing.invoice.paid", "amount": 100}, sort_keys=True).encode("utf-8")

    expected_mac = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    generated_mac = WebhookDispatcher.sign_payload(payload, secret)
    assert generated_mac == expected_mac

    assert WebhookDispatcher.verify_signature(payload, secret, generated_mac) is True
    assert WebhookDispatcher.verify_signature(payload, "invalid_secret", generated_mac) is False

    tampered_payload = json.dumps({"event": "billing.invoice.paid", "amount": 999}, sort_keys=True).encode("utf-8")
    assert WebhookDispatcher.verify_signature(tampered_payload, secret, generated_mac) is False


def test_audit_logger_tracks_lifecycle() -> None:
    """Test audit log entries are generated for tenant mutations."""
    mgr = SaaSModeManager(ExecutionMode.SAAS)
    tenant = mgr.provision_tenant("Audit Org", "audit_owner")
    mgr.create_project("audit_owner", "audited_proj")

    entries = mgr._audit.get_tenant_entries(tenant.tenant_id)
    assert len(entries) >= 2

    actions = [e.action for e in entries]
    assert "tenant.provision" in actions
    assert "project.create" in actions


def test_standalone_mode_unrestricted() -> None:
    """Test that standalone mode creates projects directly without requiring tenant records."""
    mgr = SaaSModeManager(ExecutionMode.STANDALONE)
    project = mgr.create_project("local_dev", "offline_proj")
    assert project["project_id"] == "offline_proj"
    assert project["tenant_id"] == "standalone_tenant"


def test_verifier_all_invariants_pass() -> None:
    """Test that SaaSModeVerifier executes all 10 architectural invariants successfully."""
    verifier = SaaSModeVerifier()
    results = verifier.verify_all_invariants()
    assert results["all_passed"] is True
    assert results["passed_checks"] == 10
    assert results["total_checks"] == 10
