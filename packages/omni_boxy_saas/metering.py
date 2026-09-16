"""Token consumption metering, sliding-window rate limiting, and quota enforcement."""

import time
from collections import deque
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from packages.omni_boxy_saas.models import Tenant, UsageRecord


class UsageMeter:
    """Monitors token usage, pr review quotas, and sliding-window rate limits per tenant."""

    def __init__(self) -> None:
        """Initialize usage records and sliding-window rate limiting timestamp queues."""
        self._usage_by_tenant_period: Dict[str, UsageRecord] = {}
        self._request_timestamps: Dict[str, deque] = {}
        self._token_timestamps: Dict[str, deque] = {}

    def _get_period_key(self, tenant_id: str, period: Optional[str] = None) -> str:
        """Compute compound key for tenant and billing period."""
        active_period = period or datetime.now(timezone.utc).strftime("%Y-%m")
        return f"{tenant_id}:{active_period}"

    def get_or_create_usage(self, tenant_id: str, period: Optional[str] = None) -> UsageRecord:
        """Fetch active period usage record or initialize zeroed record."""
        active_period = period or datetime.now(timezone.utc).strftime("%Y-%m")
        key = f"{tenant_id}:{active_period}"
        if key not in self._usage_by_tenant_period:
            self._usage_by_tenant_period[key] = UsageRecord(tenant_id=tenant_id, period=active_period)
        return self._usage_by_tenant_period[key]

    def record_tokens(
        self,
        tenant_id: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        period: Optional[str] = None,
    ) -> UsageRecord:
        """Increment token counters and record sliding-window token event."""
        usage = self.get_or_create_usage(tenant_id, period)
        usage.input_tokens += max(0, input_tokens)
        usage.output_tokens += max(0, output_tokens)
        usage.cached_tokens += max(0, cached_tokens)

        now = time.time()
        if tenant_id not in self._token_timestamps:
            self._token_timestamps[tenant_id] = deque()
        total_increment = input_tokens + output_tokens + cached_tokens
        self._token_timestamps[tenant_id].append((now, total_increment))

        return usage

    def record_review(self, tenant_id: str, period: Optional[str] = None) -> UsageRecord:
        """Increment daily review invocation tally for tenant."""
        usage = self.get_or_create_usage(tenant_id, period)
        usage.reviews_count += 1
        return usage

    def record_container_spawn(self, tenant_id: str, period: Optional[str] = None) -> UsageRecord:
        """Increment count of sandboxed containers initiated by tenant."""
        usage = self.get_or_create_usage(tenant_id, period)
        usage.containers_spawned += 1
        return usage

    def is_monthly_quota_exceeded(self, tenant: Tenant, period: Optional[str] = None) -> bool:
        """Verify if current month tokens exceed subscribed plan ceiling."""
        usage = self.get_or_create_usage(tenant.tenant_id, period)
        return usage.total_tokens >= tenant.max_monthly_tokens

    def check_rate_limit(
        self,
        tenant_id: str,
        max_requests_per_minute: int = 60,
        max_tokens_per_minute: int = 100_000,
        requested_tokens: int = 0,
        window_seconds: float = 60.0,
    ) -> Tuple[bool, str]:
        """Verify request and token velocity against sliding-window limits."""
        now = time.time()
        cutoff = now - window_seconds

        if tenant_id not in self._request_timestamps:
            self._request_timestamps[tenant_id] = deque()
        req_queue = self._request_timestamps[tenant_id]
        while req_queue and req_queue[0] < cutoff:
            req_queue.popleft()

        if len(req_queue) >= max_requests_per_minute:
            res = (False, "Request rate limit exceeded")
            return res

        if tenant_id not in self._token_timestamps:
            self._token_timestamps[tenant_id] = deque()
        tok_queue = self._token_timestamps[tenant_id]
        while tok_queue and tok_queue[0][0] < cutoff:
            tok_queue.popleft()

        current_window_tokens = sum(item[1] for item in tok_queue)
        if current_window_tokens + requested_tokens > max_tokens_per_minute:
            res = (False, "Token rate limit exceeded")
            return res

        req_queue.append(now)
        res = (True, "Rate limit check passed")
        return res

    def get_usage_summary(self, tenant_id: str, period: Optional[str] = None) -> UsageRecord:
        """Retrieve point-in-time usage statement for specified billing cycle."""
        return self.get_or_create_usage(tenant_id, period)
