"""
Root entrypoint for Issue #302: Secure HMAC-SHA256 JSON Session Cache.

Re-exports core cryptographic session caching primitives to guarantee backward
compatibility with both root-level and deliverables-level imports.
"""

from __future__ import annotations

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

__all__ = [
    "SecureSessionCache",
    "SecureSessionSerializer",
    "SecurityTamperError",
    "SerializationError",
    "SessionError",
    "SessionExpiredError",
    "SessionNotFoundError",
    "safe_b64decode",
    "safe_b64encode",
    "validate_safe_json_types",
]
