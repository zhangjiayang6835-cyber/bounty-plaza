"""
Comprehensive Unit Test Suite for Issue #302: Secure Session Cache.

Tests HMAC-SHA256 authenticated JSON serialization, base64 encoding, anti-tampering,
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
    from deliverables.issue_302.session_cache import (
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
except ImportError:
    from session_cache import (  # type: ignore
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


class MockRedisBackend:
    """Mock Redis client implementing get, set, and delete."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        """Get value by key."""
        return self.store.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> None:  # pylint: disable=unused-argument
        """Set key value."""
        self.store[key] = value

    def delete(self, key: str) -> bool:
        """Delete key."""
        return self.store.pop(key, None) is not None


class TestSecureSessionCache(unittest.TestCase):
    """Test suite for SecureSessionCache and SecureSessionSerializer."""

    def setUp(self) -> None:
        """Set up test instances and keys."""
        self.secret_key = "secure_test_secret_key_bounty_302"
        self.serializer = SecureSessionSerializer(self.secret_key)
        self.cache = SecureSessionCache(self.secret_key, default_ttl=3600)

    def test_normal_save_and_retrieve(self) -> None:
        """Verify normal session save and retrieve flow."""
        session_id = "sess_user_98765"
        payload = {
            "user_id": 101,
            "username": "bounty_hunter",
            "roles": ["researcher", "auditor"],
            "authenticated": True,
            "score": 99.9,
            "meta": None,
        }

        token = self.cache.save(session_id, payload)
        self.assertIsInstance(token, str)
        self.assertIn(".", token)

        retrieved = self.cache.retrieve(session_id)
        self.assertEqual(retrieved, payload)
        self.assertTrue(self.cache.exists(session_id))

    def test_direct_dumps_and_loads(self) -> None:
        """Verify direct dumps and loads helper methods."""
        data = {"theme": "cyber_dark", "volume": 85, "active": True}
        token = self.cache.dumps(data)
        loaded = self.cache.loads(token)
        self.assertEqual(loaded, data)

    def test_base64_utilities(self) -> None:
        """Verify safe base64 encoding and decoding with automatic padding."""
        test_bytes = b"Testing safe base64 URL encoding 12345!"
        encoded = safe_b64encode(test_bytes)
        self.assertIsInstance(encoded, str)
        decoded = safe_b64decode(encoded)
        self.assertEqual(decoded, test_bytes)

        # Test padding resilience
        unpadded = encoded.rstrip("=")
        decoded_unpadded = safe_b64decode(unpadded)
        self.assertEqual(decoded_unpadded, test_bytes)

    def test_tampered_payload_rejection(self) -> None:
        """Verify that modifying payload bytes triggers SecurityTamperError."""
        data = {"user_id": 500, "role": "viewer"}
        token = self.serializer.pack(data)
        sig, payload = token.split(".", 1)

        # Tamper payload
        tampered_payload = payload[:-2] + ("A" if payload[-2] != "A" else "B") + payload[-1]
        tampered_token = f"{sig}.{tampered_payload}"

        with self.assertRaises(SecurityTamperError):
            self.serializer.unpack(tampered_token)

    def test_tampered_signature_rejection(self) -> None:
        """Verify that modifying the HMAC signature triggers SecurityTamperError."""
        data = {"user_id": 500, "role": "viewer"}
        token = self.serializer.pack(data)
        sig, payload = token.split(".", 1)

        # Alter the first character of hex signature
        altered_char = "0" if sig[0] != "0" else "1"
        forged_sig = altered_char + sig[1:]
        tampered_token = f"{forged_sig}.{payload}"

        with self.assertRaises(SecurityTamperError):
            self.serializer.unpack(tampered_token)

    def test_secret_key_mismatch(self) -> None:
        """Verify that tokens signed with a different key are rejected."""
        data = {"account_id": "ACC_888"}
        token = self.serializer.pack(data)

        attacker_serializer = SecureSessionSerializer("wrong_secret_key_value")
        with self.assertRaises(SecurityTamperError):
            attacker_serializer.unpack(token)

    def test_reject_type_injection_and_unsafe_objects(self) -> None:
        """Ensure arbitrary objects, functions and classes are rejected."""
        class MaliciousPayload:  # pylint: disable=too-few-public-methods
            """Simulate arbitrary class injection."""

        unsafe_cases = [
            {"exploit": MaliciousPayload()},
            {"callback": lambda x: x},
            {"callable": int},
            {"buffer": b"raw_bytes"},
        ]
        for unsafe_data in unsafe_cases:
            with self.assertRaises(SerializationError):
                self.serializer.pack(unsafe_data)

    def test_reject_non_dict_root(self) -> None:
        """Ensure session data must be a dictionary."""
        with self.assertRaises(SerializationError):
            self.serializer.pack("plain string not a dict")  # type: ignore

        with self.assertRaises(SerializationError):
            self.serializer.pack([1, 2, 3])  # type: ignore

    def test_reject_non_string_dict_keys(self) -> None:
        """Ensure non-string dictionary keys are rejected."""
        invalid_data = {1234: "numeric_key_val"}
        with self.assertRaises(SerializationError):
            validate_safe_json_types(invalid_data)

    def test_deep_nesting_depth_limit(self) -> None:
        """Ensure deeply nested recursive structures are rejected."""
        deep: dict[str, Any] = {"level": 0}
        curr = deep
        for depth_idx in range(60):
            curr["next"] = {"level": depth_idx}
            curr = curr["next"]

        with self.assertRaises(SerializationError):
            validate_safe_json_types(deep)

    def test_ttl_expiration(self) -> None:
        """Verify expired sessions raise SessionExpiredError."""
        session_id = "sess_ttl_expire"
        data = {"role": "temporary"}

        # Store with TTL 1 second
        self.cache.save(session_id, data, ttl=1)
        self.assertEqual(self.cache.retrieve(session_id), data)

        # Fast forward time simulation
        token = self.cache._get_raw(session_id)  # pylint: disable=protected-access
        self.assertIsNotNone(token)
        sig, payload_repr = token.split(".", 1)

        raw_json = safe_b64decode(payload_repr).decode("utf-8")
        env = json.loads(raw_json)
        env["expires_at"] = int(time.time()) - 10  # Expired 10s ago

        tampered_json = json.dumps(env, sort_keys=True, separators=(",", ":"))
        new_b64 = safe_b64encode(tampered_json.encode("utf-8"))
        valid_sig_expired = self.serializer._compute_signature(new_b64.encode("ascii"))  # pylint: disable=protected-access
        expired_token = f"{valid_sig_expired}.{new_b64}"

        self.cache._set_raw(session_id, expired_token)  # pylint: disable=protected-access

        with self.assertRaises(SessionExpiredError):
            self.cache.retrieve(session_id)

    def test_max_age_enforcement(self) -> None:
        """Verify max_age parameter in unpack raises SessionExpiredError."""
        data = {"session": "old_session"}
        now = int(time.time()) - 200

        env = {
            "v": 1,
            "created_at": now,
            "expires_at": None,
            "nonce": "testnonce12345678",
            "data": data,
        }
        payload_str = json.dumps(env, sort_keys=True, separators=(",", ":"))
        payload_b64 = safe_b64encode(payload_str.encode("utf-8"))
        sig = self.serializer._compute_signature(payload_b64.encode("ascii"))  # pylint: disable=protected-access
        token = f"{sig}.{payload_b64}"

        with self.assertRaises(SessionExpiredError):
            self.serializer.unpack(token, max_age=100)

    def test_future_timestamp_skew_rejection(self) -> None:
        """Verify future timestamp drift triggers SecurityTamperError."""
        data = {"session": "future_session"}
        future_time = int(time.time()) + 1000

        env = {
            "v": 1,
            "created_at": future_time,
            "expires_at": None,
            "nonce": "skewnonce1234567",
            "data": data,
        }
        payload_str = json.dumps(env, sort_keys=True, separators=(",", ":"))
        payload_b64 = safe_b64encode(payload_str.encode("utf-8"))
        sig = self.serializer._compute_signature(payload_b64.encode("ascii"))  # pylint: disable=protected-access
        token = f"{sig}.{payload_b64}"

        with self.assertRaises(SecurityTamperError):
            self.serializer.unpack(token)

    def test_malformed_tokens(self) -> None:
        """Verify various malformed token strings raise appropriate errors."""
        malformed_cases = [
            "",
            "no_period_delimiter",
            ".missing_signature",
            "missing_payload.",
            "part1.part2.part3",
        ]
        for token in malformed_cases:
            with self.assertRaises(SessionError):
                self.serializer.unpack(token)

    def test_safe_get_returns_default(self) -> None:
        """Verify cache.get() returns default on missing or broken session."""
        self.assertIsNone(self.cache.get("non_existent_key"))
        self.assertEqual(self.cache.get("non_existent_key", default={"fallback": 1}), {"fallback": 1})

    def test_cache_delete_and_exists(self) -> None:
        """Verify session deletion and exists check."""
        session_id = "sess_delete_me"
        self.cache.save(session_id, {"key": "val"})
        self.assertTrue(self.cache.exists(session_id))

        deleted = self.cache.delete(session_id)
        self.assertTrue(deleted)
        self.assertFalse(self.cache.exists(session_id))
        self.assertIsNone(self.cache.get(session_id))

    def test_cache_clear(self) -> None:
        """Verify clear empties all in-memory cache contents."""
        self.cache.save("sess_1", {"num": 1})
        self.cache.save("sess_2", {"num": 2})
        self.assertTrue(self.cache.exists("sess_1"))
        self.assertTrue(self.cache.exists("sess_2"))

        self.cache.clear()
        self.assertFalse(self.cache.exists("sess_1"))
        self.assertFalse(self.cache.exists("sess_2"))

    def test_missing_session_raises_not_found(self) -> None:
        """Verify retrieve raises SessionNotFoundError on absent key."""
        with self.assertRaises(SessionNotFoundError):
            self.cache.retrieve("completely_absent_session_id")

    def test_invalid_session_id(self) -> None:
        """Verify empty or non-string session IDs raise ValueError."""
        with self.assertRaises(ValueError):
            self.cache.save("", {"foo": "bar"})

        with self.assertRaises(ValueError):
            self.cache.retrieve("")

    def test_invalid_secret_key(self) -> None:
        """Verify invalid secret keys raise ValueError or TypeError."""
        with self.assertRaises(ValueError):
            SecureSessionSerializer("")

        with self.assertRaises(TypeError):
            SecureSessionSerializer(12345)  # type: ignore

    def test_bytes_methods(self) -> None:
        """Verify pack_bytes and unpack_bytes helpers."""
        data = {"hello": "world"}
        token_bytes = self.serializer.pack_bytes(data)
        self.assertIsInstance(token_bytes, bytes)
        unpacked = self.serializer.unpack_bytes(token_bytes)
        self.assertEqual(unpacked, data)

    def test_raw_json_unpack_compatibility(self) -> None:
        """Verify unpack can handle unencoded raw JSON format for compatibility."""
        data = {"compatible": True}
        token = self.serializer.pack(data, use_base64=False)
        self.assertIn("{", token)
        unpacked = self.serializer.unpack(token)
        self.assertEqual(unpacked, data)

    def test_redis_mock_backend(self) -> None:
        """Verify pluggable Redis backend integration."""
        mock_backend = MockRedisBackend()
        redis_cache = SecureSessionCache(self.secret_key, backend=mock_backend)

        session_id = "sess_redis_test"
        payload = {"storage": "redis_mock"}
        redis_cache.save(session_id, payload)

        self.assertTrue(mock_backend.get(session_id) is not None)
        self.assertEqual(redis_cache.retrieve(session_id), payload)

        deleted = redis_cache.delete(session_id)
        self.assertTrue(deleted)
        self.assertIsNone(mock_backend.get(session_id))


if __name__ == "__main__":
    unittest.main()
