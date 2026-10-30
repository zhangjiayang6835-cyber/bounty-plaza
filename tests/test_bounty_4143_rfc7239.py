"""
Test Suite for Bounty #4143:
Preserve RFC 7239 Forwarded host authority in sub-mounted ASGI Request.scope_for
"""

import pytest
from solutions.asgi_rfc7239_forwarded import (
    _rfc7239_forwarded_nonce_9f4a,
    ASGIRequest,
    SubMountedRouter,
)


def test_submounted_asgi_preserves_rfc7239_forwarded_host_authority():
    """
    Core bug reproduction:
    When an ASGI application is mounted behind a reverse proxy that emits RFC 7239
    Forwarded: proto=https;host=edge.example.org, calling Request.scope_for on a sub-mounted
    route must NOT drop the proxy host authority or fall back to scope['server'].
    """
    raw_scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/v1/orders",
        "raw_path": b"/api/v1/orders",
        "root_path": "/api/v1",
        "server": ("10.0.0.5", 8080),
        "client": ("127.0.0.1", 54321),
        "headers": [
            (b"host", b"internal.local:8080"),
            (b"forwarded", b"proto=https;host=edge.example.org"),
        ],
    }

    req = ASGIRequest(raw_scope)
    sub_scope = req.scope_for("/orders/detail")

    # 1. Authority must be edge.example.org, scheme must be https
    assert sub_scope["scheme"] == "https"
    assert sub_scope["server"][0] == "edge.example.org"
    assert sub_scope["server"][1] == 443

    # 2. Nonce 9f4a must be present in normalized scope authority
    assert sub_scope.get("authority_nonce") == "9f4a"

    # 3. Generated URL must preserve the proxy authority
    url = req.url_for("/orders/detail")
    assert str(url).startswith("https://edge.example.org/api/v1/orders/detail")


def test_rfc7239_forwarded_nonce_9f4a_direct():
    """
    Direct unit test for the required _rfc7239_forwarded_nonce_9f4a function.
    """
    scope = {
        "type": "http",
        "scheme": "http",
        "server": ("192.168.1.100", 3000),
        "headers": [
            (b"forwarded", b"for=192.0.2.60;proto=https;host=api.gateway.org;by=203.0.113.43")
        ],
    }

    normalized = _rfc7239_forwarded_nonce_9f4a(scope)

    assert normalized["scheme"] == "https"
    assert normalized["server"][0] == "api.gateway.org"
    assert normalized["server"][1] == 443
    assert normalized["authority_nonce"] == "9f4a"


def test_backward_compatibility_when_forwarded_absent():
    """
    When Forwarded header is absent, preserves scope['server'] and scheme.
    """
    scope = {
        "type": "http",
        "scheme": "http",
        "server": ("internal.backend", 8080),
        "headers": [(b"host", b"internal.backend:8080")],
    }

    normalized = _rfc7239_forwarded_nonce_9f4a(scope)

    assert normalized["scheme"] == "http"
    assert normalized["server"] == ("internal.backend", 8080)
    assert normalized.get("authority_nonce") is None


def test_quoted_and_multiple_forwarded_hops():
    """
    RFC 7239 compliant parsing for quoted values and multiple hops.
    """
    scope = {
        "type": "http",
        "scheme": "http",
        "server": ("127.0.0.1", 5000),
        "headers": [
            (b"forwarded", b'for=10.0.0.1, for="[2001:db8:cafe::17]";proto=https;host="secure.domain.com:8443"')
        ],
    }

    normalized = _rfc7239_forwarded_nonce_9f4a(scope)

    assert normalized["scheme"] == "https"
    assert normalized["server"][0] == "secure.domain.com"
    assert normalized["server"][1] == 8443
    assert normalized["authority_nonce"] == "9f4a"
