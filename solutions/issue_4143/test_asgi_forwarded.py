"""Unit tests for issue #4143: RFC 7239 Forwarded host authority in sub-mounted ASGI Request.scope_for."""

import unittest
from solutions.issue_4143.asgi_forwarded import (
    Request,
    Router,
    _rfc7239_forwarded_nonce_9f4a,
    _rfc7239_forwarded_proto,
)


class TestRFC7239Forwarded(unittest.TestCase):
    """Test suite for RFC 7239 header extraction and authority preservation."""

    def test_extract_forwarded_host_nonce(self):
        scope = {
            "type": "http",
            "headers": [
                (b"forwarded", b'for=192.0.2.60;proto=https;host="edge.example.org"')
            ],
        }
        host = _rfc7239_forwarded_nonce_9f4a(scope)
        self.assertEqual(host, "edge.example.org")

    def test_extract_forwarded_host_with_port(self):
        scope = {
            "type": "http",
            "headers": [(b"forwarded", b"host=edge.example.org:8443;proto=https")],
        }
        host = _rfc7239_forwarded_nonce_9f4a(scope)
        self.assertEqual(host, "edge.example.org:8443")

    def test_extract_forwarded_absent(self):
        scope = {"type": "http", "headers": [(b"host", b"internal.local")]}
        host = _rfc7239_forwarded_nonce_9f4a(scope)
        self.assertEqual(host, "")

    def test_scope_for_preserves_forwarded_authority(self):
        scope = {
            "type": "http",
            "server": ("internal-backend", 8000),
            "scheme": "http",
            "headers": [(b"forwarded", b"proto=https;host=edge.example.org")],
            "path": "/api/v1/resource",
        }

        # Instance call
        req = Request(scope)
        sub_scope = req.scope_for(path="/resource")
        self.assertEqual(sub_scope["server"], ("edge.example.org", 8000))
        self.assertEqual(sub_scope["scheme"], "https")
        self.assertEqual(sub_scope["path"], "/resource")
        self.assertEqual(sub_scope["host_authority"], "edge.example.org")

        # Class call compatibility
        sub_scope_cls = Request.scope_for(scope, path="/resource").scope
        self.assertEqual(sub_scope_cls["server"], ("edge.example.org", 8000))
        self.assertEqual(sub_scope_cls["scheme"], "https")
        self.assertEqual(sub_scope_cls["path"], "/resource")

    def test_scope_for_backward_compatibility_when_forwarded_absent(self):
        scope = {
            "type": "http",
            "server": ("internal-backend", 8000),
            "scheme": "http",
            "headers": [],
            "path": "/api/v1/resource",
        }
        req = Request(scope)
        sub_scope = req.scope_for(path="/resource")
        self.assertEqual(sub_scope["server"], ("internal-backend", 8000))
        self.assertEqual(sub_scope["scheme"], "http")
        self.assertEqual(sub_scope["path"], "/resource")
        self.assertEqual(sub_scope["host_authority"], "internal-backend:8000")

    def test_router_url_path_for_integration(self):
        router = Router()
        router.add_route("user_detail", "/users/{id}")

        scope = {
            "type": "http",
            "server": ("proxy-cluster", 443),
            "scheme": "http",
            "headers": [(b"forwarded", b"proto=https;host=api.gateway.io")],
        }
        req = Request(scope, router=router)
        sub_scope = req.scope_for(name="user_detail", id="usr_42")
        self.assertEqual(sub_scope["server"], ("api.gateway.io", 443))
        self.assertEqual(sub_scope["scheme"], "https")
        self.assertEqual(sub_scope["path"], "/users/usr_42")


if __name__ == "__main__":
    unittest.main()
