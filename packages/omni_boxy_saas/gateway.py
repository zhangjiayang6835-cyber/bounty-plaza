"""Boxy SaaS Gateway unifying multi-tenant routing, webhook handling, and billing."""

import json
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple
from packages.omni_boxy_saas.bitcoin_billing import BitcoinBillingEngine
from packages.omni_boxy_saas.metering import UsageMeter
from packages.omni_boxy_saas.models import (
    ApiKeyRecord,
    BountySettlement,
    Tenant,
    TenantStatus,
    TenantTier,
)
from packages.omni_boxy_saas.security import (
    BoxySafetyFilter,
    verify_webhook_signature,
)
from packages.omni_boxy_saas.sticky_notes import StickyNoteStore
from packages.omni_boxy_saas.tenant_manager import TIER_POLICIES, TenantManager
from packages.omni_boxy_saas.tools_dispatcher import BoxyToolsDispatcher


class BoxySaasGateway:
    """Central gateway for Boxy multi-tenant SaaS operations, webhooks, and billing."""

    def __init__(self, default_btc_rate: Decimal = Decimal("65000.00")) -> None:
        """Initialize all underlying SaaS components."""
        self.tenants = TenantManager()
        self.meter = UsageMeter()
        self.notes = StickyNoteStore()
        self.safety = BoxySafetyFilter()
        self.dispatcher = BoxyToolsDispatcher(
            sticky_store=self.notes,
            usage_meter=self.meter,
            safety_filter=self.safety,
        )
        self.billing = BitcoinBillingEngine(default_btc_usd_rate=default_btc_rate)

    def register_tenant(
        self,
        tenant_id: str,
        org_name: str,
        tier: str = "free",
        contact_email: str = "",
    ) -> Tenant:
        """Register a new tenant under specified subscription tier."""
        clean_tier = TenantTier(tier.lower())
        tenant = self.tenants.create_tenant(
            tenant_id=tenant_id,
            org_name=org_name,
            tier=clean_tier,
            contact_email=contact_email,
            status=TenantStatus.ACTIVE,
        )
        return tenant

    def issue_tenant_key(self, tenant_id: str, name: str = "default") -> Tuple[str, ApiKeyRecord]:
        """Issue an API key for calling tenant."""
        key_tuple = self.tenants.issue_api_key(tenant_id=tenant_id, name=name)
        return key_tuple

    def handle_github_webhook(
        self,
        event_type: str,
        delivery_id: str,
        signature_header: str,
        raw_payload_bytes: bytes,
        webhook_secret: str,
    ) -> Dict[str, Any]:
        """Verify HMAC signature and dispatch GitHub event to mapped tenant."""
        is_valid = verify_webhook_signature(
            payload_bytes=raw_payload_bytes,
            signature_header=signature_header,
            secret=webhook_secret,
        )
        if not is_valid:
            raise PermissionError("Invalid GitHub webhook signature")

        payload = json.loads(raw_payload_bytes.decode("utf-8"))
        repo_info = payload.get("repository", {})
        repo_full_name = repo_info.get("full_name", "")

        tenant = self.tenants.get_tenant_for_repo(repo_full_name)
        if not tenant:
            result = {
                "status": "ignored",
                "reason": f"Repository '{repo_full_name}' is not registered under any tenant",
                "delivery_id": delivery_id,
                "event": event_type,
            }
            return result

        if tenant.status != TenantStatus.ACTIVE:
            raise PermissionError(f"Tenant '{tenant.tenant_id}' is inactive")

        action = payload.get("action", "")
        self.meter.record_tokens(
            tenant_id=tenant.tenant_id,
            input_tokens=len(str(payload).split()) // 3,
            output_tokens=20,
            cached_tokens=0,
        )

        result = {
            "status": "processed",
            "delivery_id": delivery_id,
            "tenant_id": tenant.tenant_id,
            "repository": repo_full_name,
            "event": event_type,
            "action": action,
        }
        return result

    def execute_tool(
        self,
        raw_api_key: str,
        tool_name: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Authenticate caller via API key and execute designated Boxy tool."""
        tenant = self.tenants.authenticate_key(raw_api_key)
        if not tenant:
            raise PermissionError("Invalid or inactive API credentials")

        rate_ok, rate_reason = self.meter.check_rate_limit(
            tenant_id=tenant.tenant_id,
            max_requests_per_minute=120,
            max_tokens_per_minute=200_000,
        )
        if not rate_ok:
            raise RuntimeError(rate_reason)

        if self.meter.is_monthly_quota_exceeded(tenant):
            raise RuntimeError("Monthly token quota exceeded. Please upgrade tier.")

        if tool_name == "save_sticky_note":
            res = self.dispatcher.execute_save_sticky_note(
                tenant=tenant,
                repo_full_name=params.get("repo_full_name", ""),
                title=params.get("title", ""),
                content=params.get("content", ""),
                author=params.get("author", "boxy-bot"),
                tags=params.get("tags"),
            )
            return res

        if tool_name == "get_sticky_notes":
            res = self.dispatcher.execute_get_sticky_notes(
                tenant=tenant,
                repo_full_name=params.get("repo_full_name"),
            )
            return res

        if tool_name == "react_comment":
            res = self.dispatcher.execute_react_comment(
                tenant=tenant,
                comment_id=int(params.get("comment_id", 0)),
                reaction=params.get("reaction", ""),
            )
            return res

        if tool_name == "label_issue":
            res = self.dispatcher.execute_label_issue(
                tenant=tenant,
                issue_number=int(params.get("issue_number", 0)),
                label=params.get("label", ""),
            )
            return res

        if tool_name == "review_pr":
            res = self.dispatcher.execute_review_pr(
                tenant=tenant,
                pr_number=int(params.get("pr_number", 0)),
                diff_text=params.get("diff_text", ""),
            )
            return res

        if tool_name == "run_sandboxed_command":
            res = self.dispatcher.execute_sandboxed_command(
                tenant=tenant,
                command_line=params.get("command_line", ""),
            )
            return res

        raise ValueError(f"Unknown tool name: '{tool_name}'")

    def create_bitcoin_subscription(
        self,
        tenant_id: str,
        tier: str,
        btc_rate_usd: Optional[Decimal] = None,
    ) -> Dict[str, Any]:
        """Generate Bitcoin invoice for upgrading tenant subscription tier."""
        tenant = self.tenants.get_tenant(tenant_id)
        if not tenant:
            raise KeyError(f"Tenant '{tenant_id}' not found")

        clean_tier = TenantTier(tier.lower())
        policy = TIER_POLICIES.get(clean_tier)
        if not policy:
            raise ValueError(f"Invalid tier: {tier}")

        invoice = self.billing.create_invoice(
            tenant_id=tenant_id,
            amount_usd=policy.price_usd,
            btc_rate_usd=btc_rate_usd,
        )

        res = {
            "invoice_id": invoice.invoice_id,
            "tenant_id": invoice.tenant_id,
            "target_tier": clean_tier.value,
            "amount_usd": str(invoice.amount_usd),
            "amount_btc": str(invoice.amount_btc),
            "amount_satoshis": invoice.amount_satoshis,
            "address": invoice.address,
            "bip21_uri": invoice.bip21_uri,
            "status": invoice.status.value,
        }
        return res

    def settle_bitcoin_subscription(
        self,
        invoice_id: str,
        txid: str,
        target_tier: str,
    ) -> Dict[str, Any]:
        """Confirm Bitcoin payment and immediately elevate tenant subscription tier."""
        confirmed_invoice = self.billing.confirm_invoice(invoice_id=invoice_id, txid=txid)
        clean_tier = TenantTier(target_tier.lower())
        updated_tenant = self.tenants.update_tier(
            tenant_id=confirmed_invoice.tenant_id,
            new_tier=clean_tier,
        )
        res = {
            "status": "confirmed",
            "invoice_id": confirmed_invoice.invoice_id,
            "tenant_id": updated_tenant.tenant_id,
            "new_tier": updated_tenant.tier.value,
            "max_monthly_tokens": updated_tenant.max_monthly_tokens,
            "max_reviews_per_day": updated_tenant.max_reviews_per_day,
            "max_concurrent_containers": updated_tenant.max_concurrent_containers,
            "txid": confirmed_invoice.txid,
        }
        return res

    def compute_bounty_breakdown(
        self,
        bounty_usd: Decimal = Decimal("99999999.00"),
        btc_rate_usd: Decimal = Decimal("65000.00"),
    ) -> BountySettlement:
        """Calculate complete financial payout breakdown for Bounty Plaza Issue #1570."""
        settlement = self.billing.calculate_bounty_settlement(
            bounty_usd=bounty_usd,
            btc_rate_usd=btc_rate_usd,
        )
        return settlement
