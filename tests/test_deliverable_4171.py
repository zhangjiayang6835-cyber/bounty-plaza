"""Root test suite for deliverable_4171.py."""

from deliverable_4171 import (
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


def test_root_deliverable_unquote_token():
    """Verify unquoting strips quotes and handles backslash escapes."""
    assert unquote_token("edge.example.org") == "edge.example.org"
    assert unquote_token('"edge.example.org"') == "edge.example.org"
    assert unquote_token('""') == ""
    assert unquote_token('"escaped \\"quote\\""') == 'escaped "quote"'
    assert unquote_token('"backslash \\\\ test"') == "backslash \\ test"


def test_root_deliverable_split_host_and_port():
    """Verify host and port resolution."""
    h1, p1 = split_host_and_port("edge.example.org:8443", "https")
    assert h1 == "edge.example.org"
    assert p1 == 8443

    h2, p2 = split_host_and_port("[2001:db8:cafe::17]:4711", "https")
    assert h2 == "2001:db8:cafe::17"
    assert p2 == 4711


def test_root_deliverable_submounted_scope_for():
    """Verify submounted scope_for preserves outer proxy authority."""
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


def test_root_deliverable_backward_compat():
    """Verify fallback when Forwarded header is absent."""
    scope = {
        "type": "http",
        "scheme": "http",
        "server": ("localhost", 8080),
        "path": "/status",
        "root_path": "",
        "headers": [(b"host", b"localhost:8080")],
    }
    req = Request(scope)
    assert req.url == "http://localhost:8080/status"
    sub_scope = req.scope_for("/status")
    assert sub_scope["server"] == ("localhost", 8080)
