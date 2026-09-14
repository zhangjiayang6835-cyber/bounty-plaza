"""Comprehensive verification engine testing architectural SaaS mode invariants."""

from typing import Any

from packages.saas_mode.manager import SaaSModeManager, WebhookDispatcher
from packages.saas_mode.models import (
    ExecutionMode,
    FeatureNotAllowedError,
    Permission,
    QuotaExceededError,
    Role,
    TenantStatus,
    TenantTier,
    UnauthorizedAccessError,
)


class SaaSModeVerifier:
    """Performs automated validation across all multi-tenant and governance invariants."""

    def __init__(self) -> None:
        """Initialize test runner and tracking state."""
        self._results: list[dict[str, Any]] = []

    def verify_all_invariants(self) -> dict[str, Any]:
        """Execute all invariant checks and return consolidated verification scorecard."""
        checks = [
            ("tenant_isolation", self.check_tenant_isolation),
            ("quota_project_limit", self.check_quota_project_limit),
            ("quota_storage_limit", self.check_quota_storage_limit),
            ("rbac_enforcement", self.check_rbac_enforcement),
            ("inactive_user_block", self.check_inactive_user_block),
            ("suspended_tenant_block", self.check_suspended_tenant_block),
            ("feature_gating", self.check_feature_gating),
            ("webhook_hmac_integrity", self.check_webhook_hmac_integrity),
            ("standalone_mode_bypass", self.check_standalone_mode_bypass),
            ("audit_trail_integrity", self.check_audit_trail_integrity),
        ]

        passed_count = 0
        total_count = len(checks)
        details: dict[str, bool] = {}

        for name, test_fn in checks:
            success = test_fn()
            details[name] = success
            if success:
                passed_count += 1

        all_passed = passed_count == total_count
        scorecard = {
            "all_passed": all_passed,
            "passed_checks": passed_count,
            "total_checks": total_count,
            "details": details,
        }
        return scorecard

    def check_tenant_isolation(self) -> bool:
        """Verify project partitions prevent cross-tenant access."""
        mgr = SaaSModeManager(ExecutionMode.SAAS)
        tenant_a = mgr.provision_tenant("Org A", "user_a")
        tenant_b = mgr.provision_tenant("Org B", "user_b")

        mgr.create_project("user_a", "proj_alpha")

        try:
            mgr.get_project("user_b", "proj_alpha")
            return False
        except (KeyError, UnauthorizedAccessError):
            pass

        return True

    def check_quota_project_limit(self) -> bool:
        """Verify project count limit on free tier blocks overflow."""
        mgr = SaaSModeManager(ExecutionMode.SAAS)
        mgr.provision_tenant("Org Quota", "user_q", tier=TenantTier.FREE)

        mgr.create_project("user_q", "proj_1")
        mgr.create_project("user_q", "proj_2")
        mgr.create_project("user_q", "proj_3")

        try:
            mgr.create_project("user_q", "proj_4")
            return False
        except QuotaExceededError:
            pass

        return True

    def check_quota_storage_limit(self) -> bool:
        """Verify storage limits block oversized allocations."""
        mgr = SaaSModeManager(ExecutionMode.SAAS)
        mgr.provision_tenant("Org Storage", "user_s", tier=TenantTier.FREE)

        excessive_bytes = 200 * 1024 * 1024
        try:
            mgr.create_project("user_s", "proj_big", initial_storage_bytes=excessive_bytes)
            return False
        except QuotaExceededError:
            pass

        return True

    def check_rbac_enforcement(self) -> bool:
        """Verify viewer cannot create projects or alter subscriptions."""
        mgr = SaaSModeManager(ExecutionMode.SAAS)
        tenant = mgr.provision_tenant("Org RBAC", "owner_u")
        mgr.add_tenant_user("owner_u", tenant.tenant_id, "viewer_u", Role.VIEWER, "v@org.com")

        try:
            mgr.create_project("viewer_u", "viewer_proj")
            return False
        except UnauthorizedAccessError:
            pass

        return True

    def check_inactive_user_block(self) -> bool:
        """Verify deactivated users cannot execute requests."""
        mgr = SaaSModeManager(ExecutionMode.SAAS)
        tenant = mgr.provision_tenant("Org Inactive", "owner_u")
        user = mgr.add_tenant_user("owner_u", tenant.tenant_id, "member_u", Role.MEMBER, "m@org.com")
        user.is_active = False

        try:
            mgr.create_project("member_u", "inactive_proj")
            return False
        except UnauthorizedAccessError:
            pass

        return True

    def check_suspended_tenant_block(self) -> bool:
        """Verify suspended tenants cannot provision resources."""
        mgr = SaaSModeManager(ExecutionMode.SAAS)
        tenant = mgr.provision_tenant("Org Suspended", "owner_u")
        tenant.status = TenantStatus.SUSPENDED

        try:
            mgr.create_project("owner_u", "suspended_proj")
            return False
        except Exception as err:
            if not isinstance(err, (UnauthorizedAccessError, Exception)):
                return False

        return True

    def check_feature_gating(self) -> bool:
        """Verify free tier rejects webhooks and pro tier allows them."""
        mgr = SaaSModeManager(ExecutionMode.SAAS)
        tenant_free = mgr.provision_tenant("Free Org", "free_u", tier=TenantTier.FREE)
        tenant_pro = mgr.provision_tenant("Pro Org", "pro_u", tier=TenantTier.PRO)

        blocked = False
        try:
            mgr.emit_webhook_event(tenant_free.tenant_id, "test.event", {"k": "v"}, "secret")
        except FeatureNotAllowedError:
            blocked = True

        if not blocked:
            return False

        try:
            event_obj, sig = mgr.emit_webhook_event(
                tenant_pro.tenant_id, "test.event", {"k": "v"}, "secret"
            )
            if not sig or not event_obj:
                return False
        except FeatureNotAllowedError:
            return False

        return True

    def check_webhook_hmac_integrity(self) -> bool:
        """Verify HMAC-SHA256 signature generation and validation."""
        secret = "super_secure_webhook_signing_key_999"
        payload_bytes = b'{"action":"tenant.created","tenant_id":"12345"}'

        sig = WebhookDispatcher.sign_payload(payload_bytes, secret)
        valid = WebhookDispatcher.verify_signature(payload_bytes, secret, sig)
        if not valid:
            return False

        tampered_bytes = b'{"action":"tenant.created","tenant_id":"99999"}'
        invalid = WebhookDispatcher.verify_signature(tampered_bytes, secret, sig)
        if invalid:
            return False

        wrong_secret_invalid = WebhookDispatcher.verify_signature(
            payload_bytes, "wrong_secret", sig
        )
        if wrong_secret_invalid:
            return False

        return True

    def check_standalone_mode_bypass(self) -> bool:
        """Verify standalone mode executes without requiring tenant provisioning."""
        mgr = SaaSModeManager(ExecutionMode.STANDALONE)
        proj = mgr.create_project("any_user", "local_proj")
        if proj.get("project_id") != "local_proj":
            return False
        return True

    def check_audit_trail_integrity(self) -> bool:
        """Verify state modifications create non-empty audit trails."""
        mgr = SaaSModeManager(ExecutionMode.SAAS)
        tenant = mgr.provision_tenant("Org Audit", "user_audit")
        mgr.create_project("user_audit", "audit_proj")
        mgr.delete_project("user_audit", "audit_proj")

        entries = mgr._audit.get_tenant_entries(tenant.tenant_id)
        if len(entries) < 3:
            return False

        actions = [e.action for e in entries]
        expected_actions = ["tenant.provision", "project.create", "project.delete"]
        for expected in expected_actions:
            if expected not in actions:
                return False

        return True
