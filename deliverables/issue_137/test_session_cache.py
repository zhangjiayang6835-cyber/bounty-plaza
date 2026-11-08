"""
Comprehensive Unit Test Suite for Issue #137: Secure Session Cache.

Tests HMAC-SHA256 authenticated JSON serialization, anti-tampering,
type safety, expiration constraints, and error handling.
"""

from __future__ import annotations

import json
import sys
import time
import unittest
from pathlib import Path

# Add repo root and module dir to path if needed
CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

try:
    from deliverables.issue_137.session_cache import (
        SecureSessionCache,
        SecureSessionSerializer,
        SecurityTamperError,
        SerializationError,
        SessionError,
        SessionExpiredError,
        SessionNotFoundError,
    )
except ImportError:
    from session_cache import (  # type: ignore
        SecureSessionCache,
        SecureSessionSerializer,
        SecurityTamperError,
        SerializationError,
        SessionError,
        SessionExpiredError,
        SessionNotFoundError,
    )


class MockRedisBackend:
    """Mock Redis client implementing get, set, and delete."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> None:  # pylint: disable=unused-argument
        self.store[key] = value

    def delete(self, key: str) -> bool:
        return self.store.pop(key, None) is not None


class TestSecureSessionCache(unittest.TestCase):
    """Test suite for SecureSessionCache and SecureSessionSerializer."""

    def setUp(self) -> None:
        """Set up test instances and keys."""
        self.secret_key = "secure_test_secret_key_bounty_137"
        self.serializer = SecureSessionSerializer(self.secret_key)
        self.cache = SecureSessionCache(self.secret_key, default_ttl=3600)

    def test_normal_save_and_retrieve(self) -> None:
        """Verify normal session save and retrieve flow."""
        session_id = "sess_user_12345"
        payload = {
            "user_id": 42,
            "username": "alice",
            "roles": ["admin", "editor"],
            "authenticated": True,
        }

        token = self.cache.save(session_id, payload)
        self.assertIsInstance(token, str)
        self.assertIn(".", token)

        retrieved = self.cache.retrieve(session_id)
        self.assertEqual(retrieved, payload)
        self.assertTrue(self.cache.exists(session_id))

    def test_direct_dumps_and_loads(self) -> None:
        """Verify direct dumps and loads helper methods."""
        data = {"theme": "dark", "score": 99.5, "active": True}
        token = self.cache.dumps(data)
        loaded = self.cache.loads(token)
        self.assertEqual(loaded, data)

    def test_tampered_payload_rejection(self) -> None:
        """Verify that modifying payload bytes triggers SecurityTamperError."""
        data = {"user_id": 100, "role": "guest"}
        token = self.serializer.pack(data)
        sig, payload_json = token.split(".", 1)

        # Alter payload JSON to elevate privilege
        tampered_json = payload_json.replace('"guest"', '"admin"')
        tampered_token = f"{sig}.{tampered_json}"

        with self.assertRaises(SecurityTamperError):
            self.serializer.unpack(tampered_token)

    def test_tampered_signature_rejection(self) -> None:
        """Verify that modifying the signature triggers SecurityTamperError."""
        data = {"session": "data"}
        token = self.serializer.pack(data)
        sig, payload_json = token.split(".", 1)

        # Invert the first character of HMAC signature
        flipped_char = "a" if sig[0] != "a" else "b"
        bad_sig = flipped_char + sig[1:]
        tampered_token = f"{bad_sig}.{payload_json}"

        with self.assertRaises(SecurityTamperError):
            self.serializer.unpack(tampered_token)

    def test_malformed_json_rejection(self) -> None:
        """Verify that corrupted JSON payload is rejected."""
        # Forge signature for broken JSON
        bad_payload = "not_valid_{json: true"
        sig = self.serializer._compute_signature(bad_payload.encode("utf-8"))  # pylint: disable=protected-access
        token = f"{sig}.{bad_payload}"

        with self.assertRaises(SerializationError):
            self.serializer.unpack(token)

    def test_malformed_token_format(self) -> None:
        """Verify that tokens missing delimiters or components are rejected."""
        with self.assertRaises(SerializationError):
            self.serializer.unpack("")

        with self.assertRaises(SecurityTamperError):
            self.serializer.unpack("nodotintoken")

        with self.assertRaises(SecurityTamperError):
            self.serializer.unpack(".payload")

        with self.assertRaises(SecurityTamperError):
            self.serializer.unpack("signature.")

    def test_empty_missing_key_handling(self) -> None:
        """Verify handling of empty, invalid, and missing session keys."""
        with self.assertRaises(ValueError):
            self.cache.save("", {"foo": "bar"})

        with self.assertRaises(ValueError):
            self.cache.retrieve("")

        with self.assertRaises(SessionNotFoundError):
            self.cache.retrieve("non_existent_session_id")

        self.assertFalse(self.cache.exists("non_existent_session_id"))
        self.assertIsNone(self.cache.get("non_existent_session_id"))
        self.assertEqual(self.cache.get("non_existent_session_id", default="fallback"), "fallback")

    def test_expired_ttl_handling(self) -> None:
        """Verify that sessions past their TTL raise SessionExpiredError."""
        session_id = "sess_short_lived"
        data = {"temp": "token"}

        # Store with TTL of -10 seconds (already expired)
        token = self.cache.save(session_id, data, ttl=-10)

        # Unpack directly should notice expiration
        # Note: if ttl <= 0, expires_at is None unless passed as expired envelope
        now = int(time.time())
        expired_envelope = {
            "v": 1,
            "created_at": now - 100,
            "expires_at": now - 10,
            "nonce": "testnonce",
            "data": data,
        }
        expired_str = json.dumps(expired_envelope, sort_keys=True, separators=(",", ":"))
        sig = self.serializer._compute_signature(expired_str.encode("utf-8"))  # pylint: disable=protected-access
        expired_token = f"{sig}.{expired_str}"

        with self.assertRaises(SessionExpiredError):
            self.serializer.unpack(expired_token)

        self.cache._set_raw(session_id, expired_token)  # pylint: disable=protected-access
        with self.assertRaises(SessionExpiredError):
            self.cache.retrieve(session_id)

    def test_max_age_handling(self) -> None:
        """Verify max_age enforcement on unpack."""
        data = {"created": "in_past"}
        now = int(time.time())
        old_envelope = {
            "v": 1,
            "created_at": now - 500,
            "expires_at": None,
            "nonce": "oldnonce",
            "data": data,
        }
        raw_str = json.dumps(old_envelope, sort_keys=True, separators=(",", ":"))
        sig = self.serializer._compute_signature(raw_str.encode("utf-8"))  # pylint: disable=protected-access
        token = f"{sig}.{raw_str}"

        with self.assertRaises(SessionExpiredError):
            self.serializer.unpack(token, max_age=300)

    def test_future_timestamp_drift_rejection(self) -> None:
        """Verify that timestamps unreasonably far in the future are rejected."""
        data = {"time_traveler": True}
        future_time = int(time.time()) + 1000
        future_envelope = {
            "v": 1,
            "created_at": future_time,
            "expires_at": None,
            "nonce": "future_nonce",
            "data": data,
        }
        raw_str = json.dumps(future_envelope, sort_keys=True, separators=(",", ":"))
        sig = self.serializer._compute_signature(raw_str.encode("utf-8"))  # pylint: disable=protected-access
        token = f"{sig}.{raw_str}"

        with self.assertRaises(SecurityTamperError):
            self.serializer.unpack(token)

    def test_rejection_of_unsupported_malicious_types(self) -> None:
        """Verify that arbitrary non-JSON types (e.g., functions, custom objects) are rejected."""
        class MaliciousObject:
            """Arbitrary user-defined object to simulate exploit injection."""
            def __reduce__(self):
                return (id, (42,))

        with self.assertRaises(SerializationError):
            self.serializer.pack({"exploit": MaliciousObject()})

        with self.assertRaises(SerializationError):
            self.serializer.pack({"func": lambda: "rce"})

        with self.assertRaises(SerializationError):
            self.serializer.pack({123: "non_string_key"})  # type: ignore

    def test_delete_and_clear(self) -> None:
        """Verify session deletion and cache clearing."""
        self.cache.save("sess_1", {"v": 1})
        self.cache.save("sess_2", {"v": 2})

        self.assertTrue(self.cache.delete("sess_1"))
        self.assertFalse(self.cache.delete("sess_1"))
        self.assertFalse(self.cache.exists("sess_1"))
        self.assertTrue(self.cache.exists("sess_2"))

        self.cache.clear()
        self.assertFalse(self.cache.exists("sess_2"))

    def test_mock_redis_backend_integration(self) -> None:
        """Verify that SecureSessionCache integrates seamlessly with external backends like Redis."""
        redis_mock = MockRedisBackend()
        cache = SecureSessionCache(self.secret_key, backend=redis_mock)

        sess_id = "redis_session_999"
        data = {"state": "active", "cart": [101, 102]}

        token = cache.save(sess_id, data, ttl=1800)
        self.assertEqual(redis_mock.get(sess_id), token)

        result = cache.retrieve(sess_id)
        self.assertEqual(result, data)

        self.assertTrue(cache.delete(sess_id))
        self.assertIsNone(redis_mock.get(sess_id))

    def test_secret_key_types(self) -> None:
        """Verify bytes and string secret key initialization."""
        serializer_bytes = SecureSessionSerializer(b"binary_secret_key_here")
        token = serializer_bytes.pack({"hello": "world"})
        self.assertEqual(serializer_bytes.unpack(token), {"hello": "world"})

        with self.assertRaises(ValueError):
            SecureSessionSerializer("")

        with self.assertRaises(TypeError):
            SecureSessionSerializer(12345)  # type: ignore


if __name__ == "__main__":
    unittest.main()
