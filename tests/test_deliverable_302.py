"""
Root Pytest Discovery Test Suite for Deliverable 302 (#302).

Validates:
- HMAC-SHA256 authenticated JSON session caching.
- Base64 encoding and safe decoding.
- Prevention of type injection and arbitrary code execution.
- Tampering detection and cryptographic signature verification.
- TTL expiration and clock skew rejection.
- Pluggable cache backends and fallbacks.
"""

from __future__ import annotations

import unittest

from deliverable_302 import (
    SecureSessionCache,
    SecureSessionSerializer,
    SecurityTamperError,
    SerializationError,
    SessionError,
    SessionExpiredError,
    SessionNotFoundError,
    safe_b64decode,
    safe_b64encode,
    validate_safe_json_types,
)
from deliverables.issue_302.test_session_cache import (
    MockRedisBackend,
    TestSecureSessionCache,
)


class TestDeliverable302RootExports(unittest.TestCase):
    """Test suite ensuring deliverable_302 correctly exports and integrates all components."""

    def setUp(self) -> None:
        """Initialize test fixtures."""
        self.secret = "root_test_secret_302"
        self.cache = SecureSessionCache(self.secret)
        self.serializer = SecureSessionSerializer(self.secret)

    def test_direct_root_imports(self) -> None:
        """Ensure all required classes and functions are callable from deliverable_302."""
        self.assertTrue(issubclass(SecurityTamperError, SessionError))
        self.assertTrue(issubclass(SessionExpiredError, SessionError))
        self.assertTrue(issubclass(SerializationError, SessionError))
        self.assertTrue(issubclass(SessionNotFoundError, SessionError))

        # Test safe type validation
        validate_safe_json_types({"valid": 1, "nested": [True, "text"]})
        with self.assertRaises(SerializationError):
            validate_safe_json_types({"bad": object()})

    def test_end_to_end_root_cache(self) -> None:
        """Verify full round-trip session save, load, and tamper resistance."""
        sess_id = "user_root_session_99"
        data = {"role": "admin", "permissions": ["read", "write"], "active": True}

        token = self.cache.save(sess_id, data)
        self.assertIsInstance(token, str)

        recovered = self.cache.retrieve(sess_id)
        self.assertEqual(recovered, data)

        # Ensure tamper detection works via root imported classes
        sig, payload = token.split(".", 1)
        bad_sig = "f" * len(sig) if sig[0] != "f" else "0" * len(sig)
        bad_token = f"{bad_sig}.{payload}"

        with self.assertRaises(SecurityTamperError):
            self.serializer.unpack(bad_token)


__all__ = ["TestDeliverable302RootExports", "TestSecureSessionCache", "MockRedisBackend"]

if __name__ == "__main__":
    unittest.main()
