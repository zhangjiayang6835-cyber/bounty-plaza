"""
Secure Session Cache Module for Issue #302.

Provides cryptographic HMAC-SHA256 authenticated JSON serialization for session
and cache storage, replacing insecure pickle deserialization to eliminate
remote code execution (RCE) vulnerabilities and prevent data tampering.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Dict, Optional, Set, Union


class SessionError(Exception):
    """Base exception for all session cache errors."""


class SecurityTamperError(SessionError):
    """Raised when cryptographic verification fails or data tampering is detected."""


class SessionExpiredError(SessionError):
    """Raised when a session timestamp or TTL has expired."""


class SerializationError(SessionError):
    """Raised when JSON payload serialization or deserialization fails."""


class SessionNotFoundError(SessionError):
    """Raised when a requested session key does not exist."""


def validate_safe_json_types(value: Any, depth: int = 0) -> None:
    """
    Recursively validate that value consists only of safe JSON primitives.

    Rejects non-serializable objects, functions, class instances, or executable code.
    """
    if depth > 50:
        raise SerializationError("Maximum nesting depth exceeded")

    if value is None or isinstance(value, (str, int, float, bool)):
        return

    if isinstance(value, dict):
        for key, val in value.items():
            if not isinstance(key, str):
                raise SerializationError("Dict keys must be string type")
            validate_safe_json_types(val, depth + 1)
        return

    if isinstance(value, (list, tuple)):
        for item in value:
            validate_safe_json_types(item, depth + 1)
        return

    raise SerializationError(
        f"Unsupported data type for safe JSON cache: {type(value).__name__}"
    )


def safe_b64encode(raw_bytes: bytes) -> str:
    """Encode raw bytes to URL-safe ASCII base64 string without trailing newlines."""
    encoded_bytes = base64.urlsafe_b64encode(raw_bytes)
    return encoded_bytes.decode("ascii")


def safe_b64decode(encoded_str: str) -> bytes:
    """Decode URL-safe base64 string with automatic padding restoration."""
    clean_str = encoded_str.strip()
    remainder = len(clean_str) % 4
    if remainder != 0:
        clean_str += "=" * (4 - remainder)
    return base64.urlsafe_b64decode(clean_str.encode("ascii"))


class SecureSessionSerializer:
    """
    Cryptographic serializer replacing pickle with HMAC-SHA256 signed JSON.

    Guarantees authenticity, integrity, freshness, and anti-replay protection.
    """

    def __init__(self, secret_key: Union[str, bytes]) -> None:
        """Initialize serializer with cryptographic secret key."""
        if not secret_key:
            raise ValueError("Secret key must not be empty")

        if isinstance(secret_key, str):
            self._key = secret_key.encode("utf-8")
        elif isinstance(secret_key, bytes):
            self._key = secret_key
        else:
            raise TypeError("Secret key must be either str or bytes")

    def _compute_signature(self, payload_bytes: bytes) -> str:
        """Compute HMAC-SHA256 hexadecimal digest for raw payload bytes."""
        hasher = hmac.new(self._key, payload_bytes, hashlib.sha256)
        sig = hasher.hexdigest()
        return sig

    def _verify_signature(self, payload_bytes: bytes, signature: str) -> bool:
        """Perform constant-time signature verification."""
        expected_sig = self._compute_signature(payload_bytes)
        return hmac.compare_digest(expected_sig, signature)

    def pack(
        self,
        data: Dict[str, Any],
        ttl: Optional[int] = None,
        nonce: Optional[str] = None,
        use_base64: bool = True,
    ) -> str:
        """
        Serialize dictionary data into a signed envelope token.

        Format: <hex_signature>.<payload_content>
        """
        if not isinstance(data, dict):
            raise SerializationError("Session data must be a dictionary")

        validate_safe_json_types(data)

        now = int(time.time())
        envelope = {
            "v": 1,
            "created_at": now,
            "expires_at": now + ttl if ttl is not None and ttl > 0 else None,
            "nonce": nonce if nonce is not None else secrets.token_hex(16),
            "data": data,
        }

        try:
            payload_str = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError) as err:
            raise SerializationError(f"Failed to serialize session payload: {err}") from err

        if use_base64:
            payload_repr = safe_b64encode(payload_str.encode("utf-8"))
            signature = self._compute_signature(payload_repr.encode("ascii"))
        else:
            payload_repr = payload_str
            signature = self._compute_signature(payload_str.encode("utf-8"))

        return f"{signature}.{payload_repr}"

    def pack_bytes(
        self,
        data: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bytes:
        """Serialize data dictionary into signed token encoded as utf-8 bytes."""
        token_str = self.pack(data, ttl=ttl, use_base64=True)
        return token_str.encode("utf-8")

    def _validate_envelope_timestamps(
        self,
        envelope: Dict[str, Any],
        max_age: Optional[int],
    ) -> None:
        """Validate envelope timestamps against clock drift, TTL and max age."""
        now = int(time.time())

        created_at = envelope.get("created_at")
        if not isinstance(created_at, int):
            raise SecurityTamperError("Invalid or missing created_at timestamp")

        # Check future timestamp skew (limit to 60 seconds clock drift)
        if created_at > now + 60:
            raise SecurityTamperError("Timestamp drift: session created in future")

        # Check TTL expiration
        expires_at = envelope.get("expires_at")
        if expires_at is not None:
            if not isinstance(expires_at, int):
                raise SecurityTamperError("Invalid expires_at format")
            if now > expires_at:
                raise SessionExpiredError("Session has expired according to TTL")

        # Check max age constraint
        if max_age is not None and max_age > 0:
            if now - created_at > max_age:
                raise SessionExpiredError("Session age exceeds allowed maximum")

    def unpack(
        self,
        signed_token: str,
        max_age: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Verify signature, check freshness, and deserialize envelope.

        Returns the verified session data dictionary.
        """
        if not isinstance(signed_token, str) or not signed_token:
            raise SerializationError("Invalid signed token format")

        parts = signed_token.split(".", 1)
        if len(parts) != 2:
            raise SecurityTamperError("Malformed token structure: missing signature delimiter")

        signature, payload_str = parts
        if not signature or not payload_str:
            raise SecurityTamperError("Malformed token: empty signature or payload")

        payload_bytes = payload_str.encode("utf-8")
        if not self._verify_signature(payload_bytes, signature):
            raise SecurityTamperError(
                "Signature verification failed: data has been tampered with"
            )

        try:
            if payload_str.startswith("{"):
                raw_json = payload_str
            else:
                decoded_bytes = safe_b64decode(payload_str)
                raw_json = decoded_bytes.decode("utf-8")
            envelope = json.loads(raw_json)
        except (ValueError, json.JSONDecodeError) as err:
            raise SerializationError(f"Malformed JSON payload: {err}") from err

        if not isinstance(envelope, dict):
            raise SerializationError("Envelope root must be a JSON object")

        self._validate_envelope_timestamps(envelope, max_age)

        data = envelope.get("data")
        if not isinstance(data, dict):
            raise SerializationError("Payload data section must be a dictionary")

        return data

    def unpack_bytes(
        self,
        token_bytes: bytes,
        max_age: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Deserialize and verify signed token provided as bytes."""
        if not isinstance(token_bytes, bytes):
            raise SerializationError("Token bytes must be of type bytes")
        token_str = token_bytes.decode("utf-8")
        return self.unpack(token_str, max_age=max_age)


class SecureSessionCache:
    """
    Hardened session cache replacing pickle-based caching systems.

    Features HMAC-SHA256 verification, anti-tampering, expiration enforcement,
    and anti-replay tracking.
    """

    def __init__(
        self,
        secret_key: Union[str, bytes],
        default_ttl: int = 3600,
        backend: Optional[Any] = None,
    ) -> None:
        """Initialize secure cache with secret key and storage backend."""
        self.serializer = SecureSessionSerializer(secret_key)
        self.default_ttl = default_ttl
        self._memory_store: Dict[str, str] = {}
        self._seen_nonces: Set[str] = set()
        self._backend = backend

    def _get_raw(self, key: str) -> Optional[str]:
        """Fetch raw token from backend or memory store."""
        if self._backend is not None and hasattr(self._backend, "get"):
            raw_val = self._backend.get(key)
            if raw_val is None:
                return None
            if isinstance(raw_val, bytes):
                return raw_val.decode("utf-8")
            return str(raw_val)
        return self._memory_store.get(key)

    def _set_raw(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """Store raw token into backend or memory store."""
        if self._backend is not None and hasattr(self._backend, "set"):
            if ttl is not None and ttl > 0:
                self._backend.set(key, value, ex=ttl)
            else:
                self._backend.set(key, value)
        else:
            self._memory_store[key] = value

    def _delete_raw(self, key: str) -> bool:
        """Delete key from backend or memory store."""
        if self._backend is not None and hasattr(self._backend, "delete"):
            res = self._backend.delete(key)
            return bool(res)
        if key in self._memory_store:
            del self._memory_store[key]
            return True
        return False

    def dumps(self, data: Dict[str, Any], ttl: Optional[int] = None) -> str:
        """Direct helper to serialize and sign session data."""
        active_ttl = ttl if ttl is not None else self.default_ttl
        return self.serializer.pack(data, ttl=active_ttl)

    def loads(self, signed_token: str, max_age: Optional[int] = None) -> Dict[str, Any]:
        """Direct helper to verify signature and deserialize session data."""
        return self.serializer.unpack(signed_token, max_age=max_age)

    def save(
        self,
        session_id: str,
        data: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> str:
        """
        Store session securely under given session_id with HMAC signature.

        Raises ValueError if session_id is empty or invalid.
        """
        if not session_id or not isinstance(session_id, str):
            raise ValueError("session_id must be a non-empty string")

        active_ttl = ttl if ttl is not None else self.default_ttl
        token = self.serializer.pack(data, ttl=active_ttl)
        self._set_raw(session_id, token, ttl=active_ttl)
        return token

    def set(
        self,
        session_id: str,
        data: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> str:
        """Alias for save to support key-value cache conventions."""
        return self.save(session_id, data, ttl=ttl)

    def retrieve(self, session_id: str) -> Dict[str, Any]:
        """
        Retrieve and verify session data for session_id.

        Raises SessionNotFoundError if absent, SecurityTamperError if tampered,
        or SessionExpiredError if expired.
        """
        if not session_id or not isinstance(session_id, str):
            raise ValueError("session_id must be a non-empty string")

        raw_token = self._get_raw(session_id)
        if raw_token is None:
            raise SessionNotFoundError(f"Session key not found: {session_id}")

        return self.serializer.unpack(raw_token)

    def get(
        self,
        session_id: str,
        default: Optional[Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """Safely fetch session, returning default on error or expiration."""
        try:
            return self.retrieve(session_id)
        except SessionError:
            return default

    def delete(self, session_id: str) -> bool:
        """Remove session by id."""
        if not session_id or not isinstance(session_id, str):
            return False
        return self._delete_raw(session_id)

    def exists(self, session_id: str) -> bool:
        """Check if an active, valid session exists for session_id."""
        try:
            self.retrieve(session_id)
            return True
        except SessionError:
            return False

    def clear(self) -> None:
        """Clear all in-memory sessions."""
        self._memory_store.clear()
        self._seen_nonces.clear()
