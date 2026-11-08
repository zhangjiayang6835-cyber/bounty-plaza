"""Comprehensive test suite for RFC 7239 Forwarded header preservation (#4168).

Validates RFC 7239 §4 and §6 compliance including quote escaping, IPv6 literals,
first-hop precedence, sub-mounted ASGI Request scope derivation, and URL generation.
"""

from __future__ import annotations

import unittest
from typing import Any, Dict, List, Optional, Tuple

try:
    from deliverables.issue_4168.rfc7239_forwarded import (
        Request,
        _rfc7239_forwarded_nonce_9f4a,
        normalize_forwarded_scope,
        parse_forwarded,
        scope_for,
    )
except ImportError:
    try:
        from .rfc7239_forwarded import (  # type: ignore[no-redef]
            Request,
            _rfc7239_forwarded_nonce_9f4a,
            normalize_forwarded_scope,
            parse_forwarded,
            scope_for,
        )
    except ImportError:
        from rfc7239_forwarded import (  # type: ignore[no-redef]
            Request,
            _rfc7239_forwarded_nonce_9f4a,
            normalize_forwarded_scope,
            parse_forwarded,
            scope_for,
        )

BASE_SCOPE: Dict[str, Any] = {
    "type": "http",
    "scheme": "http",
    "server": ("internal.local", 8000),
    "root_path": "/api",
    "headers": [],
}


def _make_scope(
    *forwarded_values: str,
    headers: Optional[List[Tuple[bytes, bytes]]] = None,
    root_path: str = "/api",
) -> Dict[str, Any]:
    """Create a test ASGI scope dictionary with Forwarded headers."""
    scope = dict(BASE_SCOPE)
    scope["root_path"] = root_path
    combined_headers: List[Tuple[bytes, bytes]] = list(headers or [])
    for val in forwarded_values:
        combined_headers.append((b"forwarded", val.encode("latin-1")))
    scope["headers"] = combined_headers
    return scope


class TestRFC7239Forwarded(unittest.TestCase):
    """Test cases for RFC 7239 Forwarded header parsing and scope derivation."""

    def test_host_and_proto_applied(self) -> None:
        """Verify host authority and proto scheme are correctly applied."""
        scope = _make_scope("proto=https;host=edge.example.org")
        normalized = _rfc7239_forwarded_nonce_9f4a(scope)
        self.assertEqual(normalized["scheme"], "https")
        self.assertEqual(normalized["server"], ("edge.example.org", 8000))

    def test_explicit_port_retained(self) -> None:
        """Verify explicit port in host directive overrides default server port."""
        scope = _make_scope("host=edge.example.org:8443")
        normalized = _rfc7239_forwarded_nonce_9f4a(scope)
        self.assertEqual(normalized["server"], ("edge.example.org", 8443))

    def test_ipv6_literal_with_port(self) -> None:
        """Verify bracketed IPv6 literals with port are parsed accurately."""
        scope = _make_scope('host="[2001:db8::1]:443";proto=https')
        normalized = _rfc7239_forwarded_nonce_9f4a(scope)
        self.assertEqual(normalized["scheme"], "https")
        self.assertEqual(normalized["server"][0], "[2001:db8::1]")
        self.assertEqual(normalized["server"][1], 443)

    def test_ipv6_literal_without_port(self) -> None:
        """Verify bracketed IPv6 literals without port retain original port."""
        scope = _make_scope('host="[2001:db8::1]";proto=https')
        normalized = _rfc7239_forwarded_nonce_9f4a(scope)
        self.assertEqual(normalized["scheme"], "https")
        self.assertEqual(normalized["server"][0], "[2001:db8::1]")
        self.assertEqual(normalized["server"][1], 8000)

    def test_first_hop_precedence(self) -> None:
        """Verify that only the first client-facing hop is used for authority."""
        scope = _make_scope("host=attacker.example, host=real.example")
        normalized = _rfc7239_forwarded_nonce_9f4a(scope)
        self.assertEqual(normalized["server"][0], "attacker.example")

    def test_quoted_commas_inside_parameter_values(self) -> None:
        """Verify commas inside quoted-strings do not trigger hop splitting."""
        scope = _make_scope('for="client1,client2";host=edge.example.org')
        normalized = _rfc7239_forwarded_nonce_9f4a(scope)
        self.assertEqual(normalized["server"][0], "edge.example.org")

    def test_missing_header_backward_compatibility(self) -> None:
        """Verify scopes without Forwarded headers remain strictly unchanged."""
        scope = dict(BASE_SCOPE)
        normalized = _rfc7239_forwarded_nonce_9f4a(scope)
        self.assertEqual(normalized["server"], ("internal.local", 8000))
        self.assertNotIn("forwarded_authority", normalized)

    def test_garbage_and_malformed_header_resilience(self) -> None:
        """Verify malformed or empty headers are safely ignored."""
        scope = _make_scope("nonsense;;=;", "proto=http;host=")
        normalized = _rfc7239_forwarded_nonce_9f4a(scope)
        self.assertEqual(normalized["scheme"], "http")
        self.assertEqual(normalized["server"], ("internal.local", 8000))

    def test_submount_scope_for_path_preservation(self) -> None:
        """Verify sub-mounted Request.scope_for preserves authority and resolves path."""
        scope = _make_scope("proto=https;host=edge.example.org")
        req = Request(scope)
        derived = req.scope_for("/widgets")
        self.assertEqual(derived["scheme"], "https")
        self.assertEqual(derived["server"][0], "edge.example.org")
        self.assertEqual(derived["path"], "/api/widgets")
        self.assertEqual(derived["raw_path"], b"/api/widgets")

    def test_submount_scope_for_already_prefixed(self) -> None:
        """Verify sub-mounted Request.scope_for does not duplicate prefix if present."""
        scope = _make_scope("proto=https;host=edge.example.org")
        req = Request(scope)
        derived = req.scope_for("/api/widgets")
        self.assertEqual(derived["path"], "/api/widgets")

    def test_root_path_resolution(self) -> None:
        """Verify relative path resolution when application has no root_path."""
        scope = _make_scope("host=edge.example.org", root_path="")
        req = Request(scope, root_path="")
        derived = req.scope_for("/widgets")
        self.assertEqual(derived["path"], "/widgets")
        self.assertEqual(derived["server"][0], "edge.example.org")

    def test_scope_for_backward_compatibility_without_forwarded(self) -> None:
        """Verify scope_for without Forwarded headers preserves original authority."""
        req = Request(dict(BASE_SCOPE))
        derived = req.scope_for("/widgets")
        self.assertEqual(derived["server"], ("internal.local", 8000))
        self.assertEqual(derived["path"], "/api/widgets")

    def test_case_insensitive_proto_and_header(self) -> None:
        """Verify case insensitivity for header name and proto values."""
        scope = dict(BASE_SCOPE)
        scope["headers"] = [(b"FORWARDED", b"Proto=WSS;host=ws.example.org")]
        normalized = _rfc7239_forwarded_nonce_9f4a(scope)
        self.assertEqual(normalized["scheme"], "wss")
        self.assertEqual(normalized["server"][0], "ws.example.org")

    def test_resolve_path_helper(self) -> None:
        """Verify resolve_path helper method on Request."""
        req = Request(dict(BASE_SCOPE), root_path="/api")
        resolved = req.resolve_path("/status")
        self.assertEqual(resolved, "/api/status")

    def test_parse_forwarded_multi_directives(self) -> None:
        """Verify complete parsing of by, for, host, proto directives."""
        hdr = (
            'by=192.0.2.1;for="[2001:db8::1]:8080";host="edge.example.org:443";proto=https, '
            'for=_gazonk;proto=http'
        )
        hops = parse_forwarded(hdr)
        self.assertEqual(len(hops), 2)
        self.assertEqual(hops[0]["by"], "192.0.2.1")
        self.assertEqual(hops[0]["for"], "[2001:db8::1]:8080")
        self.assertEqual(hops[0]["host"], "edge.example.org:443")
        self.assertEqual(hops[0]["proto"], "https")
        self.assertEqual(hops[1]["for"], "_gazonk")
        self.assertEqual(hops[1]["proto"], "http")

    def test_escaped_quotes_and_backslashes(self) -> None:
        """Verify backslash escapes inside quoted strings."""
        hdr = r'for="\"escaped\"";by="\\slash\\"'
        hops = parse_forwarded(hdr)
        self.assertEqual(len(hops), 1)
        self.assertEqual(hops[0]["for"], '"escaped"')
        self.assertEqual(hops[0]["by"], "\\slash\\")

    def test_url_for_generation_standard_port(self) -> None:
        """Verify url_for omits default port 443 for https."""
        scope = _make_scope("proto=https;host=example.com:443")
        req = Request(scope, root_path="/api")
        url = req.url_for("/dashboard")
        self.assertEqual(url, "https://example.com/api/dashboard")

    def test_url_for_generation_custom_port(self) -> None:
        """Verify url_for includes custom port."""
        scope = _make_scope('proto=https;host="[2001:db8::1]:8443"')
        req = Request(scope, root_path="/v1")
        url = req.url_for("/metrics")
        self.assertEqual(url, "https://[2001:db8::1]:8443/v1/metrics")

    def test_standalone_scope_for_function(self) -> None:
        """Verify top-level scope_for function produces identical scope."""
        scope = _make_scope("proto=https;host=edge.example.org")
        derived = scope_for(scope, "/items", root_path="/api")
        self.assertEqual(derived["scheme"], "https")
        self.assertEqual(derived["server"][0], "edge.example.org")
        self.assertEqual(derived["path"], "/api/items")


if __name__ == "__main__":
    unittest.main(verbosity=2)
