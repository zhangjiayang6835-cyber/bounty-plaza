"""Tests for the deterministic RPC failover client."""

from __future__ import annotations

from typing import Dict, List

import pytest

from rpc_failover import (
    AllEndpointsFailedError,
    Endpoint,
    FailoverPolicy,
    RpcFailoverClient,
    TransportResult,
)


class FakeTransport:
    """Deterministic transport whose per-endpoint behaviour is scripted."""

    def __init__(self, outcomes: Dict[str, bool], values: Dict[str, str] = None) -> None:
        """Store the scripted outcomes and optional response values."""
        self.outcomes = dict(outcomes)
        self.values = dict(values or {})
        self.calls: List[str] = []

    def __call__(self, url: str, payload: str) -> TransportResult:
        """Return the scripted result and record the call."""
        self.calls.append(url)
        if self.outcomes.get(url, False):
            value = self.values.get(url, payload)
            return TransportResult.success(value)
        return TransportResult.failure("timeout")


def make_client(outcomes, policy=None, clock=lambda: 0, values=None):
    """Build a client plus fake transport over the given outcome map."""
    endpoints = [Endpoint(url=url, priority=priority)
                 for priority, url in enumerate(sorted(outcomes, reverse=True))]
    client = RpcFailoverClient(endpoints, policy or FailoverPolicy(), clock=clock)
    return client, FakeTransport(outcomes, values)


def test_endpoint_requires_url() -> None:
    """Empty urls and non-positive weights are rejected."""
    with pytest.raises(ValueError):
        Endpoint(url="")
    with pytest.raises(ValueError):
        Endpoint(url="https://a.example", weight=0)


def test_policy_validation() -> None:
    """Invalid policy values are rejected."""
    with pytest.raises(ValueError):
        FailoverPolicy(max_attempts=0)
    with pytest.raises(ValueError):
        FailoverPolicy(cooldown_ticks=-1)


def test_client_requires_endpoints() -> None:
    """A client cannot be built without endpoints."""
    with pytest.raises(ValueError):
        RpcFailoverClient([])


def test_success_on_first_endpoint() -> None:
    """The highest priority healthy endpoint serves the request."""
    client, transport = make_client({"https://a.example": True, "https://b.example": True})
    assert client.send("ping", transport) == "ping"
    assert transport.calls == ["https://a.example"]


def test_failover_to_second_endpoint() -> None:
    """A failing primary is retried on the next candidate."""
    client, transport = make_client({"https://a.example": False, "https://b.example": True})
    assert client.send("ping", transport) == "ping"
    assert transport.calls == ["https://a.example", "https://b.example"]


def test_all_endpoints_failed_raises() -> None:
    """Exhausting every candidate raises with the attempt trail."""
    client, transport = make_client({"https://a.example": False, "https://b.example": False})
    with pytest.raises(AllEndpointsFailedError) as excinfo:
        client.send("ping", transport)
    assert len(excinfo.value.attempts) == 2


def test_attempt_budget_is_bounded() -> None:
    """The client never exceeds max_attempts transport calls."""
    outcomes = {"https://a.example": False, "https://b.example": False,
                "https://c.example": False}
    client, transport = make_client(outcomes, policy=FailoverPolicy(max_attempts=2))
    with pytest.raises(AllEndpointsFailedError):
        client.send("ping", transport)
    assert len(transport.calls) == 2


def test_circuit_breaker_opens_after_threshold() -> None:
    """Repeated failures move the endpoint into cooldown."""
    outcomes = {"https://a.example": False, "https://b.example": True}
    client, transport = make_client(outcomes, policy=FailoverPolicy(failure_threshold=2))
    client.send("ping", transport)
    client.send("ping", transport)
    assert client.state_of("https://a.example").cooldown_until >= 0
    assert "https://a.example" not in [e.url for e in client.candidates()]


def test_cooldown_expires() -> None:
    """Once cooldown elapses the endpoint becomes a candidate again."""
    outcomes = {"https://a.example": False, "https://b.example": True}
    ticks = {"now": 0}

    def clock() -> int:
        return ticks["now"]

    client, transport = make_client(outcomes, policy=FailoverPolicy(
        failure_threshold=1, cooldown_ticks=3), clock=clock)
    client.send("ping", transport)
    assert client.candidates() == [e for e in client.candidates()
                                   if e.url == "https://b.example"]
    ticks["now"] = 4
    urls = [e.url for e in client.candidates()]
    assert urls == ["https://a.example", "https://b.example"]


def test_success_resets_consecutive_failures() -> None:
    """A success clears the breaker counters."""
    outcomes = {"https://a.example": True}
    client, transport = make_client(outcomes)
    client.state_of("https://a.example").record_failure(0, client.policy)
    client.send("ping", transport)
    assert client.state_of("https://a.example").consecutive_failures == 0


def test_endpoint_ordering_is_stable() -> None:
    """Candidates are ordered by descending priority then url."""
    endpoints = [
        Endpoint(url="https://low.example", priority=1),
        Endpoint(url="https://high.example", priority=9),
        Endpoint(url="https://mid.example", priority=5),
    ]
    client = RpcFailoverClient(endpoints)
    assert [e.url for e in client.candidates()] == [
        "https://high.example", "https://mid.example", "https://low.example",
    ]


def test_values_from_transport_are_returned() -> None:
    """A scripted response value is propagated to the caller."""
    client, transport = make_client({"https://a.example": True},
                                    values={"https://a.example": "PONG"})
    assert client.send("ping", transport) == "PONG"


def test_snapshot_reports_counters() -> None:
    """The snapshot exposes per-endpoint counters."""
    client, transport = make_client({"https://a.example": False, "https://b.example": True})
    client.send("ping", transport)
    snap = client.snapshot()
    assert snap["https://a.example"]["failures"] == 1
    assert snap["https://b.example"]["successes"] == 1


def test_no_available_endpoint_error() -> None:
    """When every endpoint is cooling down the error mentions it."""
    outcomes = {"https://a.example": False, "https://b.example": True}
    client, transport = make_client(outcomes, policy=FailoverPolicy(
        failure_threshold=1, cooldown_ticks=10))
    client.state_of("https://a.example").cooldown_until = 99
    client.state_of("https://b.example").cooldown_until = 99
    with pytest.raises(AllEndpointsFailedError) as excinfo:
        client.send("ping", transport)
    assert excinfo.value.attempts == ["no-available-endpoint"]


def test_transport_result_helpers() -> None:
    """TransportResult helpers build the expected shapes."""
    ok = TransportResult.success("value")
    bad = TransportResult.failure("boom")
    assert ok.ok is True and ok.value == "value"
    assert bad.ok is False and bad.error == "boom"
