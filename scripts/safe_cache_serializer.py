"""Safe Cache Serialization & Pickle RCE Neutralization Engine.
Resolves Issue #302: Python Pickle Deserialization RCE via Cache ($200 USD).

Implements:
1. Native JSON-first serialization for untrusted session and cache payloads.
2. Cryptographic HMAC-SHA256 signature verification for cache payload integrity.
3. Timestamp-based replay and expiration protection.
4. Tamper detection and strict defense against arbitrary object instantiation/RCE.
"""

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Dict, Optional, Union


class CacheSecurityError(ValueError):
    """Base exception for cache serialization security errors."""
    pass


class DeserializationSecurityError(CacheSecurityError):
    """Raised when dangerous deserialization artifacts or malformed payloads are encountered."""
    pass


class SignatureVerificationError(CacheSecurityError):
    """Raised when HMAC signature fails verification (data tampering detected)."""
    pass


class CacheExpiredError(CacheSecurityError):
    """Raised when signed cache entry has exceeded its maximum lifetime."""
    pass


class SafeCacheSerializer:
    """Secure cache serializer replacing unsafe pickle operations with cryptographically signed JSON envelopes."""

    def __init__(
        self,
        signing_key: Optional[Union[str, bytes]] = None,
        default_ttl_seconds: int = 86400,
    ):
        if signing_key is None:
            self._key = secrets.token_bytes(32)
        elif isinstance(signing_key, str):
            self._key = signing_key.encode("utf-8")
        else:
            self._key = signing_key
        self.default_ttl_seconds = default_ttl_seconds

    def dumps(
        self,
        obj: Any,
        ttl_seconds: Optional[int] = None,
    ) -> str:
        """Serializes Python object into a signed, tamper-proof JSON envelope string.

        Envelope structure:
        {
            "version": "1.0",
            "created_at": <float>,
            "ttl": <int>,
            "payload_b64": "<base64 encoded JSON string>",
            "signature": "<hmac-sha256 hex>"
        }
        """
        try:
            json_bytes = json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8")
        except (TypeError, ValueError) as err:
            raise DeserializationSecurityError(f"Object is not JSON-serializable: {err}") from err

        payload_b64 = base64.b64encode(json_bytes).decode("ascii")
        created_at = time.time()
        ttl = self.default_ttl_seconds if ttl_seconds is None else ttl_seconds

        body_to_sign = f"{payload_b64}:{created_at:.4f}:{ttl}".encode("utf-8")
        signature = hmac.new(self._key, body_to_sign, hashlib.sha256).hexdigest()

        envelope = {
            "version": "1.0",
            "created_at": created_at,
            "ttl": ttl,
            "payload_b64": payload_b64,
            "signature": signature,
        }
        return json.dumps(envelope, separators=(",", ":"))

    def loads(
        self,
        serialized_envelope: Union[str, bytes],
        enforce_ttl: bool = True,
    ) -> Any:
        """Validates envelope signature, checks TTL, and deserializes payload.

        Rejects untrusted byte sequences, tampering, and malicious gadgets.
        """
        if isinstance(serialized_envelope, bytes):
            # Proactively reject raw pickle bytecode stream headers (\x80\x03, \x80\x04, \x80\x05)
            if serialized_envelope.startswith(b"\x80") or b"cos\nsystem" in serialized_envelope:
                raise DeserializationSecurityError(
                    "Malicious pickle bytecode detected. Raw pickle streams are strictly prohibited."
                )
            try:
                serialized_envelope = serialized_envelope.decode("utf-8")
            except UnicodeDecodeError as err:
                raise DeserializationSecurityError("Malformed non-UTF-8 payload") from err

        try:
            envelope = json.loads(serialized_envelope)
        except json.JSONDecodeError as err:
            raise DeserializationSecurityError(f"Invalid JSON envelope: {err}") from err

        if not isinstance(envelope, dict):
            raise DeserializationSecurityError("Envelope must be a JSON dictionary")

        required_keys = {"version", "created_at", "ttl", "payload_b64", "signature"}
        if not required_keys.issubset(envelope.keys()):
            raise DeserializationSecurityError(f"Missing required envelope keys: {required_keys - envelope.keys()}")

        payload_b64 = envelope["payload_b64"]
        created_at = float(envelope["created_at"])
        ttl = int(envelope["ttl"])
        received_signature = envelope["signature"]

        # 1. Verify HMAC Signature
        body_to_verify = f"{payload_b64}:{created_at:.4f}:{ttl}".encode("utf-8")
        expected_signature = hmac.new(self._key, body_to_verify, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(expected_signature, received_signature):
            raise SignatureVerificationError("HMAC signature mismatch: Cache payload has been tampered with")

        # 2. Check Expiration
        now = time.time()
        if enforce_ttl and ttl > 0:
            if now - created_at > ttl:
                raise CacheExpiredError(
                    f"Cache payload expired: age {now - created_at:.1f}s exceeds TTL {ttl}s"
                )

        # 3. Decode Payload
        try:
            raw_json = base64.b64decode(payload_b64.encode("ascii")).decode("utf-8")
            return json.loads(raw_json)
        except Exception as err:
            raise DeserializationSecurityError(f"Failed to decode verified payload: {err}") from err
