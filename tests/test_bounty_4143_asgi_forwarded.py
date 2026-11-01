"""Unit and Integration Test Suite for Issue #4143.

Validates:
1. Parsing and normalization of RFC 7239 `Forwarded` directives via `_rfc7239_forwarded_nonce_9f4a`.
2. Preservation of outer reverse-proxy host authority across sub-mounted ASGI scopes (`Request.scope_for`).
3. Port extraction across standard, custom, and IPv6 bracketed host authorities.
4. Backward compatibility when `Forwarded` header is absent.
5. Header name case-insensitivity and multiple proxy hops.
"""

from pathlib import Path
import sys
import pytest

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from solutions.asgi_forwarded_host_authority import (
    Request,
    _rfc7239_forwarded_nonce_9f4a,
    _split_host_and_port,
    _unquote_header_token,
)


def test_unquote_header_token():
    """Verify quoted strings are stripped according to RFC 7239 section 4."""
    assert _unquote_header_token('"edge.example.org"') == "edge.example.org"
    assert _unquote_header_token('edge.example.org') == "edge.example.org"
    assert _unquote_header_token('""') == ""


def test_split_host_and_port():
    """Verify host and port resolution across IPv4, hostname, and IPv6."""
    h, p = _split_host_and_port("edge.example.org:8443", "https")
    assert h == "edge.example.org"
    assert p == 8443

    h_def_https, p_def_https = _split_host_and_port("edge.example.org", "https")
    assert h_def_https == "edge.example.org"
    assert p_def_https == 443

    h_def_http, p_def_http = _split_host_and_port("edge.example.org", "http")
    assert h_def_http == "edge.example.org"
    assert p_def_http == 80

    h_ipv6, p_ipv6 = _split_host_and_port("[2001:db8:cafe::17]:4711", "https")
    assert h_ipv6 == "2001:db8:cafe::17"
    assert p_ipv6 == 4711


def test_rfc7239_forwarded_normalization_with_host_and_proto():
    """Verify Forwarded header updates scope server, scheme, and authority."""
    scope = {
        "type": "http",
        "scheme": "http",
        "server": ("127.0.0.1", 8000),
        "path": "/api/metrics",
        "headers": [
            (b"host", b"127.0.0.1:8000"),
            (b"forwarded", b"proto=https;host=edge.example.org;for=192.0.2.60"),
        ],
    }

    parsed = _rfc7239_forwarded_nonce_9f4a(scope)
    assert parsed.get("proto") == "https"
    assert parsed.get("host") == "edge.example.org"
    assert scope["server"] == ("edge.example.org", 443)
    assert scope["scheme"] == "https"
    assert scope["host_authority"] == "edge.example.org"


def test_submounted_scope_for_preserves_outer_authority():
    """Verify calling Request.scope_for preserves outer proxy authority (#4143)."""
    scope = {
        "type": "http",
        "scheme": "http",
        "server": ("10.0.0.5", 3000),
        "path": "/subapp/v1/orders/123",
        "root_path": "",
        "headers": [
            (b"host", b"10.0.0.5:3000"),
            (b"forwarded", b"proto=https;host=edge.example.org;by=203.0.113.43"),
        ],
    }

    req = Request(scope)
    assert req.scheme == "https"
    assert req.host_authority == "edge.example.org"

    sub_scope = req.scope_for("/subapp")
    assert sub_scope["server"] == ("edge.example.org", 443)
    assert sub_scope["scheme"] == "https"
    assert sub_scope["host_authority"] == "edge.example.org"
    assert sub_scope["root_path"] == "/subapp"
    assert sub_scope["path"] == "/v1/orders/123"

    sub_req = Request(sub_scope)
    assert sub_req.url == "https://edge.example.org/subapp/v1/orders/123"


def test_backward_compatibility_when_forwarded_absent():
    """Verify legacy fallback to scope['server'] when Forwarded header is absent."""
    scope = {
        "type": "http",
        "scheme": "http",
        "server": ("localhost", 8080),
        "path": "/internal/ping",
        "root_path": "",
        "headers": [(b"host", b"localhost:8080")],
    }

    req = Request(scope)
    assert req.scheme == "http"
    assert req.host_authority == "localhost:8080"
    assert req.url == "http://localhost:8080/internal/ping"

    sub_scope = req.scope_for("/internal")
    assert sub_scope["server"] == ("localhost", 8080)
    assert sub_scope["root_path"] == "/internal"
    assert sub_scope["path"] == "/ping"


def test_multi_hop_forwarded_and_case_insensitivity():
    """Verify case-insensitive header matching and multi-hop proxy chains."""
    scope = {
        "type": "http",
        "server": ("internal.proxy", 80),
        "headers": [
            (b"Forwarded", b'proto=https;host="custom-edge.com:9443", for=198.51.100.17')
        ],
    }

    parsed = _rfc7239_forwarded_nonce_9f4a(scope)
    assert parsed.get("proto") == "https"
    assert parsed.get("host") == "custom-edge.com:9443"
    assert scope["server"] == ("custom-edge.com", 9443)
    assert scope["scheme"] == "https"
    assert scope["host_authority"] == "custom-edge.com:9443"
