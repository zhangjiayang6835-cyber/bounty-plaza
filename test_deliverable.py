"""Tests for issue #4143 / #4152: Forwarded authority must survive sub-mounting."""
import unittest

from deliverable import Request, _rfc7239_forwarded_nonce_9f4a

BASE = {"type": "http", "scheme": "http", "server": ("internal.local", 8000), "root_path": "/api", "headers": []}


def scope_with(*values, headers=None):
    s = dict(BASE)
    s["headers"] = list(headers or []) + [(b"forwarded", v.encode()) for v in values]
    return s


class TestForwarded(unittest.TestCase):
    def test_host_and_proto_are_applied(self):
        s = _rfc7239_forwarded_nonce_9f4a(scope_with("proto=https;host=edge.example.org"))
        self.assertEqual(s["scheme"], "https")
        self.assertEqual(s["server"], ("edge.example.org", 8000))

    def test_explicit_port_is_kept(self):
        s = _rfc7239_forwarded_nonce_9f4a(scope_with("host=edge.example.org:8443"))
        self.assertEqual(s["server"], ("edge.example.org", 8443))

    def test_ipv6_literal(self):
        s = _rfc7239_forwarded_nonce_9f4a(scope_with('host="[2001:db8::1]:443";proto=https'))
        self.assertEqual(s["scheme"], "https")
        self.assertEqual(s["server"][0], "[2001:db8::1]")
        self.assertEqual(s["server"][1], 443)

    def test_first_hop_wins(self):
        s = _rfc7239_forwarded_nonce_9f4a(scope_with("host=attacker.example, host=real.example"))
        self.assertEqual(s["server"][0], "attacker.example")

    def test_comma_inside_quotes_is_not_a_hop_split(self):
        s = _rfc7239_forwarded_nonce_9f4a(scope_with('for="a,b";host=edge.example.org'))
        self.assertEqual(s["server"][0], "edge.example.org")

    def test_missing_header_is_backwards_compatible(self):
        s = _rfc7239_forwarded_nonce_9f4a(dict(BASE))
        self.assertEqual(s["server"], ("internal.local", 8000))
        self.assertNotIn("forwarded_authority", s)

    def test_garbage_header_is_ignored(self):
        s = _rfc7239_forwarded_nonce_9f4a(scope_with("nonsense;;=;", "proto=http;host="))
        self.assertEqual(s["scheme"], "http")
        self.assertEqual(s["server"], ("internal.local", 8000))

    def test_scope_for_keeps_outer_authority_on_sub_mount(self):
        req = Request(scope_with("proto=https;host=edge.example.org"))
        out = req.scope_for("/widgets")
        self.assertEqual(out["scheme"], "https")
        self.assertEqual(out["server"][0], "edge.example.org")
        self.assertEqual(out["path"], "/api/widgets")
        self.assertEqual(out["raw_path"], b"/api/widgets")

    def test_scope_for_without_forwarded_unchanged(self):
        req = Request(dict(BASE))
        out = req.scope_for("/widgets")
        self.assertEqual(out["server"], ("internal.local", 8000))
        self.assertEqual(out["path"], "/api/widgets")

    def test_no_root_path(self):
        req = Request(scope_with("host=edge.example.org"), root_path="")
        self.assertEqual(req.scope_for("/widgets")["path"], "/widgets")


if __name__ == "__main__":
    unittest.main(verbosity=2)
