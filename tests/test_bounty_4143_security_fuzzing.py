"""
Security Fuzzing and Path Normalization Test Suite for Bounty #4143.
Validates CWE-20 (Improper Input Validation), IPv6 host headers, and adversarial inputs.
"""

import pytest
from solutions.asgi_rfc7239_forwarded import (
    _rfc7239_forwarded_nonce_9f4a,
    ASGIRequest,
    SubMountedRouter,
)


def test_cwe_20_malformed_and_injection_headers():
    """
    CWE-20: Verifies that malformed, truncated, or hostile header strings
    do not cause crashes or unhandled exceptions.
    """
    malformed_scopes = [
        {"headers": [(b"forwarded", b"")]},
        {"headers": [(b"forwarded", b"malformed;;;;===;;")]},
        {"headers": [(b"forwarded", b"proto=;host=")]},
        {"headers": [(b"forwarded", b"host=evil.com;port=notanint")]},
        {"headers": None},
        {},
    ]

    for scope in malformed_scopes:
        normalized = _rfc7239_forwarded_nonce_9f4a(scope)
        assert isinstance(normalized, dict)


def test_ipv6_host_authority_parsing():
    """
    Validates RFC 7239 compliant handling of IPv6 bracketed addresses with and without ports.
    """
    scope = {
        "headers": [
            (b"forwarded", b'proto=https;host="[2001:db8:cafe::17]:9443"')
        ]
    }

    normalized = _rfc7239_forwarded_nonce_9f4a(scope)
    assert normalized["scheme"] == "https"
    assert normalized["server"][0] == "[2001:db8:cafe::17]"
    assert normalized["server"][1] == 9443
    assert normalized["authority_nonce"] == "9f4a"


def test_submount_router_duplicate_slashes():
    """
    Validates clean path sanitization when combining root_path and relative routes.
    """
    assert SubMountedRouter.resolve_path("/api/v1/", "/users//profile") == "/api/v1/users//profile"
    assert SubMountedRouter.resolve_path("", "test") == "/test"
    assert SubMountedRouter.resolve_path("/", "/") == "/"
    assert SubMountedRouter.resolve_path("/mount", "") == "/mount"


def test_asgi_request_dict_headers_fallback():
    """
    Validates ASGIRequest when headers are passed as a python dictionary instead of byte tuples.
    """
    scope = {
        "headers": {
            "Forwarded": "proto=https;host=cloud.service.io"
        },
        "root_path": "/v2",
    }

    req = ASGIRequest(scope)
    sub = req.scope_for("ping")
    assert sub["server"][0] == "cloud.service.io"
    assert sub["scheme"] == "https"
    assert req.url_for("ping") == "https://cloud.service.io/v2/ping"
