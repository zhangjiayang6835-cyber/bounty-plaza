"""Comprehensive test suite for RFC 7239 Forwarded header parser and ASGI authority.

Tests:
1. Quoted string unquoting with backslash escapes.
2. Delimiter splitting respecting quotes and escapes.
3. Host and port resolution across IPv4, IPv6, bracketed IPv6, and default ports.
4. Parsing directives (by, for, host, proto) with case-insensitivity.
5. ForwardedElement dataclass methods.
6. Scope normalization and outer reverse-proxy authority propagation.
7. Sub-mounted ASGI Request.scope_for URL preservation.
8. Backward compatibility when Forwarded is absent.
9. Multi-hop and multiple Forwarded headers.
10. Backward compatibility aliases.
"""

from deliverables.issue_4171.rfc7239_forwarded import (
    ForwardedElement,
    Request,
    _parse_forwarded_header,
    _rfc7239_forwarded_nonce_9f4a,
    _split_host_and_port,
    _unquote_header_token,
    normalize_asgi_scope,
    parse_forwarded_element,
    parse_forwarded_first_hop,
    parse_forwarded_header,
    split_host_and_port,
    split_quoted_string,
    unquote_token,
)


def test_unquote_token_basic_and_escapes():
    """Verify unquoting strips quotes and handles backslash escapes."""
    assert unquote_token("edge.example.org") == "edge.example.org"
    assert unquote_token('"edge.example.org"') == "edge.example.org"
    assert unquote_token('""') == ""
    assert unquote_token('"escaped \\"quote\\""') == 'escaped "quote"'
    assert unquote_token('"backslash \\\\ test"') == "backslash \\ test"
    assert unquote_token('  "spaced.org"  ') == "spaced.org"


def test_split_quoted_string():
    """Verify splitting text by delimiter respects quotes and escapes."""
    simple = "a,b,c"
    assert split_quoted_string(simple, ",") == ["a", "b", "c"]

    with_quotes = 'proto=https;host="edge.example.org,nested", for=192.0.2.1'
    elements = split_quoted_string(with_quotes, ",")
    assert len(elements) == 2
    assert elements[0] == 'proto=https;host="edge.example.org,nested"'
    assert elements[1] == "for=192.0.2.1"

    directives = split_quoted_string('for="val;semicolon";proto=https', ";")
    assert len(directives) == 2
    assert directives[0] == 'for="val;semicolon"'
    assert directives[1] == "proto=https"


def test_split_host_and_port():
    """Verify host and port resolution across IPv4, domain names, and IPv6."""
    h1, p1 = split_host_and_port("edge.example.org:8443", "https")
    assert h1 == "edge.example.org"
    assert p1 == 8443

    h2, p2 = split_host_and_port("edge.example.org", "https")
    assert h2 == "edge.example.org"
    assert p2 == 443

    h3, p3 = split_host_and_port("edge.example.org", "http")
    assert h3 == "edge.example.org"
    assert p3 == 80

    h4, p4 = split_host_and_port("[2001:db8:cafe::17]:4711", "https")
    assert h4 == "2001:db8:cafe::17"
    assert p4 == 4711

    h5, p5 = split_host_and_port("[2001:db8:cafe::17]", "https")
    assert h5 == "2001:db8:cafe::17"
    assert p5 == 443

    h6, p6 = split_host_and_port('"edge.example.org:9000"', "http")
    assert h6 == "edge.example.org"
    assert p6 == 9000

    h7, p7 = split_host_and_port('"192.168.1.1:8080"', "http")
    assert h7 == "192.168.1.1"
    assert p7 == 8080


def test_parse_forwarded_element_directives():
    """Verify parsing directives with case-insensitivity and proto normalization."""
    raw = 'By=203.0.113.43;FOR="[2001:db8::1]:8080";HOST="edge.example.org";PROTO=HTTPS;custom=value'
    parsed = parse_forwarded_element(raw)
    assert parsed["by"] == "203.0.113.43"
    assert parsed["for"] == "[2001:db8::1]:8080"
    assert parsed["host"] == "edge.example.org"
    assert parsed["proto"] == "https"
    assert parsed["custom"] == "value"


def test_forwarded_element_dataclass():
    """Verify ForwardedElement dataclass attributes and helper methods."""
    elem = ForwardedElement(
        by="203.0.113.43",
        for_param="192.0.2.60",
        host="edge.example.org",
        proto="https",
        extensions={"ext": "custom"},
    )
    assert elem.get("BY") == "203.0.113.43"
    assert elem.get("for") == "192.0.2.60"
    assert elem.get("HOST") == "edge.example.org"
    assert elem.get("Proto") == "https"
    assert elem.get("ext") == "custom"
    assert elem.get("unknown", "default_val") == "default_val"

    d = elem.to_dict()
    assert d["by"] == "203.0.113.43"
    assert d["for"] == "192.0.2.60"
    assert d["host"] == "edge.example.org"
    assert d["proto"] == "https"
    assert d["ext"] == "custom"


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

    parsed = normalize_asgi_scope(scope)
    assert parsed.get("proto") == "https"
    assert parsed.get("host") == "edge.example.org"
    assert scope["server"] == ("edge.example.org", 443)
    assert scope["scheme"] == "https"
    assert scope["host_authority"] == "edge.example.org"


def test_rfc7239_forwarded_normalization_with_ipv6():
    """Verify Forwarded header updates scope correctly for bracketed IPv6 host."""
    scope = {
        "type": "http",
        "scheme": "http",
        "server": ("127.0.0.1", 8000),
        "path": "/api/test",
        "headers": [
            (b"forwarded", b'proto=https;host="[2001:db8::1]:8080";by="_proxy"'),
        ],
    }

    parsed = normalize_asgi_scope(scope)
    assert parsed.get("proto") == "https"
    assert parsed.get("host") == "[2001:db8::1]:8080"
    assert scope["server"] == ("2001:db8::1", 8080)
    assert scope["scheme"] == "https"
    assert scope["host_authority"] == "[2001:db8::1]:8080"


def test_submounted_scope_for_preserves_outer_authority():
    """Verify calling Request.scope_for preserves outer proxy authority (#4171)."""
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


def test_nested_submounted_scope_for():
    """Verify nested sub-mounted routes preserve outer authority and accumulate root_path."""
    scope = {
        "type": "http",
        "scheme": "http",
        "server": ("10.0.0.5", 3000),
        "path": "/api/v2/items/42",
        "root_path": "",
        "headers": [
            (b"forwarded", b"proto=https;host=api.gateway.org:8443"),
        ],
    }

    req = Request(scope)
    sub1_scope = req.scope_for("/api")
    sub1_req = Request(sub1_scope)
    assert sub1_req.root_path == "/api"
    assert sub1_req.path == "/v2/items/42"
    assert sub1_req.url == "https://api.gateway.org:8443/api/v2/items/42"

    sub2_scope = sub1_req.scope_for("/v2")
    sub2_req = Request(sub2_scope)
    assert sub2_req.root_path == "/api/v2"
    assert sub2_req.path == "/items/42"
    assert sub2_req.url == "https://api.gateway.org:8443/api/v2/items/42"


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

    sub_req = Request(sub_scope)
    assert sub_req.url == "http://localhost:8080/internal/ping"


def test_multi_hop_forwarded_and_case_insensitivity():
    """Verify case-insensitive header matching and multi-hop proxy chains."""
    scope = {
        "type": "http",
        "server": ("internal.proxy", 80),
        "headers": [
            (b"Forwarded", b'proto=https;host="custom-edge.com:9443", for=198.51.100.17')
        ],
    }

    parsed = normalize_asgi_scope(scope)
    assert parsed.get("proto") == "https"
    assert parsed.get("host") == "custom-edge.com:9443"
    assert scope["server"] == ("custom-edge.com", 9443)
    assert scope["scheme"] == "https"
    assert scope["host_authority"] == "custom-edge.com:9443"


def test_multiple_forwarded_headers():
    """Verify multiple Forwarded headers in scope are merged and the first hop is used."""
    scope = {
        "type": "http",
        "server": ("local", 80),
        "headers": [
            (b"Forwarded", b"host=primary-edge.com;proto=https"),
            (b"forwarded", b"for=10.0.0.1"),
        ],
    }

    parsed = normalize_asgi_scope(scope)
    assert parsed.get("host") == "primary-edge.com"
    assert parsed.get("proto") == "https"
    assert scope["host_authority"] == "primary-edge.com"


def test_parse_forwarded_header_multi_hops():
    """Verify parse_forwarded_header returns list of all hops."""
    val = "for=192.0.2.43, for=198.51.100.17;by=203.0.113.60;proto=https"
    parsed_hops = parse_forwarded_header(val)
    assert len(parsed_hops) == 2
    assert parsed_hops[0]["for"] == "192.0.2.43"
    assert parsed_hops[1]["for"] == "198.51.100.17"
    assert parsed_hops[1]["by"] == "203.0.113.60"
    assert parsed_hops[1]["proto"] == "https"


def test_backward_compatibility_aliases():
    """Verify backward compatibility aliases match public functions."""
    assert _unquote_header_token('"foo"') == "foo"
    h, p = _split_host_and_port("foo.com:8080", "http")
    assert h == "foo.com"
    assert p == 8080
    assert _parse_forwarded_header("proto=https")["proto"] == "https"

    scope = {
        "type": "http",
        "headers": [(b"forwarded", b"proto=https;host=test.org")],
    }
    _rfc7239_forwarded_nonce_9f4a(scope)
    assert scope["scheme"] == "https"
    assert scope["server"] == ("test.org", 443)
