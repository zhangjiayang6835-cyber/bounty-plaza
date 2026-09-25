"""Deterministic RPC failover client.

This module implements a small, dependency-free failover client for JSON-RPC
style transports. It is intentionally deterministic: every decision depends
only on injected inputs (the endpoint list, the tick clock and the transport
callable), which makes the failover behaviour reproducible in tests without
any network access or sleeping.

Design goals:

* stable endpoint ordering (priority first, then declaration order),
* per-endpoint circuit breaking with a deterministic cooldown,
* a bounded attempt budget per request,
* explicit, typed failure reporting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence

__all__ = [
    "Endpoint",
    "EndpointState",
    "FailoverPolicy",
    "TransportResult",
    "AllEndpointsFailedError",
    "RpcFailoverClient",
]


@dataclass(frozen=True)
class Endpoint:
    """A single RPC endpoint declaration."""

    url: str
    priority: int = 0
    weight: int = 1

    def __post_init__(self) -> None:
        """Validate the endpoint declaration."""
        if not self.url:
            raise ValueError("endpoint url must not be empty")
        if self.weight < 1:
            raise ValueError("endpoint weight must be >= 1")


@dataclass(frozen=True)
class FailoverPolicy:
    """Tunables that control failover behaviour."""

    max_attempts: int = 3
    cooldown_ticks: int = 5
    failure_threshold: int = 2

    def __post_init__(self) -> None:
        """Validate the policy values."""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.cooldown_ticks < 0:
            raise ValueError("cooldown_ticks must be >= 0")
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")


@dataclass(frozen=True)
class TransportResult:
    """Outcome of a single transport call."""

    ok: bool
    value: Optional[str] = None
    error: Optional[str] = None

    @classmethod
    def success(cls, value: str) -> "TransportResult":
        """Build a successful transport result."""
        return cls(ok=True, value=value)

    @classmethod
    def failure(cls, error: str) -> "TransportResult":
        """Build a failed transport result."""
        return cls(ok=False, error=error)


class AllEndpointsFailedError(RuntimeError):
    """Raised when every candidate endpoint failed within the attempt budget."""

    def __init__(self, attempts: Sequence[str]) -> None:
        """Store the ordered list of attempt descriptions."""
        super().__init__("all endpoints failed: " + ", ".join(attempts))
        self.attempts: List[str] = list(attempts)


@dataclass
class EndpointState:
    """Mutable per-endpoint bookkeeping."""

    consecutive_failures: int = 0
    total_successes: int = 0
    total_failures: int = 0
    cooldown_until: int = -1
    history: List[str] = field(default_factory=list)

    def is_available(self, now: int) -> bool:
        """Return True when the endpoint is not inside its cooldown window."""
        return now >= self.cooldown_until

    def record_success(self, now: int) -> None:
        """Reset the breaker after a successful call."""
        self.consecutive_failures = 0
        self.total_successes += 1
        self.cooldown_until = -1
        self.history.append(f"ok@{now}")

    def record_failure(self, now: int, policy: FailoverPolicy) -> None:
        """Account for a failure and open the breaker when saturated."""
        self.consecutive_failures += 1
        self.total_failures += 1
        self.history.append(f"fail@{now}")
        if self.consecutive_failures >= policy.failure_threshold:
            self.cooldown_until = now + policy.cooldown_ticks


class RpcFailoverClient:
    """Route RPC payloads across a pool of endpoints with failover."""

    def __init__(
        self,
        endpoints: Sequence[Endpoint],
        policy: Optional[FailoverPolicy] = None,
        clock: Callable[[], int] = lambda: 0,
    ) -> None:
        """Create a client over ``endpoints`` using ``policy`` and ``clock``."""
        if not endpoints:
            raise ValueError("at least one endpoint is required")
        self._endpoints: List[Endpoint] = sorted(
            endpoints, key=lambda item: (-item.priority, item.url)
        )
        self._policy: FailoverPolicy = policy or FailoverPolicy()
        self._clock: Callable[[], int] = clock
        self._states: dict = {
            endpoint.url: EndpointState() for endpoint in self._endpoints
        }

    @property
    def policy(self) -> FailoverPolicy:
        """Return the active failover policy."""
        return self._policy

    def state_of(self, url: str) -> EndpointState:
        """Return the mutable state for ``url``."""
        return self._states[url]

    def candidates(self, now: Optional[int] = None) -> List[Endpoint]:
        """Return ordered endpoints that can be tried at ``now``."""
        tick = self._clock() if now is None else now
        return [
            endpoint
            for endpoint in self._endpoints
            if self._states[endpoint.url].is_available(tick)
        ]

    def send(
        self,
        payload: str,
        transport: Callable[[str, str], TransportResult],
    ) -> str:
        """Send ``payload`` through ``transport``, failing over on error."""
        attempts: List[str] = []
        for endpoint in self.candidates():
            if len(attempts) >= self._policy.max_attempts:
                break
            now = self._clock()
            result = transport(endpoint.url, payload)
            state = self._states[endpoint.url]
            if result.ok and result.value is not None:
                state.record_success(now)
                return result.value
            state.record_failure(now, self._policy)
            reason = result.error or "empty-response"
            attempts.append(f"{endpoint.url}: {reason}")
        if not attempts:
            attempts.append("no-available-endpoint")
        raise AllEndpointsFailedError(attempts)

    def snapshot(self) -> dict:
        """Return a serialisable view of the endpoint states."""
        return {
            url: {
                "successes": state.total_successes,
                "failures": state.total_failures,
                "consecutive_failures": state.consecutive_failures,
                "cooldown_until": state.cooldown_until,
            }
            for url, state in self._states.items()
        }


def main() -> None:
    """Run a tiny deterministic demonstration of the failover client."""
    endpoints = [
        Endpoint(url="https://rpc-a.example", priority=10),
        Endpoint(url="https://rpc-b.example", priority=5),
    ]
    client = RpcFailoverClient(endpoints, FailoverPolicy(), clock=lambda: 0)
    calls: List[str] = []

    def transport(url: str, payload: str) -> TransportResult:
        calls.append(url)
        if url.endswith("rpc-a.example"):
            return TransportResult.failure("timeout")
        return TransportResult.success(payload.upper())

    result = client.send("ping", transport)
    print("result:", result)
    print("calls:", calls)
    print("snapshot:", client.snapshot())


if __name__ == "__main__":
    main()
