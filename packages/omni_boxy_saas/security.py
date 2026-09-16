"""Cryptographic authentication, webhook signature validation, and payload safety filtering."""

import hashlib
import hmac
import re
import secrets
from typing import Set, Tuple


FORBIDDEN_COMMAND_PATTERNS = (
    r"rm\s+-rf\s+/",
    r"curl\s+.*\s*\|\s*(ba)?sh",
    r"wget\s+.*\s*\|\s*(ba)?sh",
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",
    r"chmod\s+777",
    r">(\s*)/dev/sd[a-z]",
    r"mkfs\.",
    r"dd\s+if=.*of=/dev/",
    r"/etc/shadow",
    r"/etc/passwd",
    r"cat\s+/dev/urandom",
    r"eval\(",
    r"exec\(",
)

ALLOWED_DEFAULT_BINARIES: Set[str] = {
    "git",
    "node",
    "npm",
    "pnpm",
    "python",
    "python3",
    "pytest",
    "cat",
    "ls",
    "echo",
    "grep",
    "diff",
}


def hash_api_key(raw_key: str) -> str:
    """Compute SHA-256 cryptographic digest of an API key."""
    digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return digest


def generate_api_key(tenant_id: str, prefix: str = "boxy_live") -> Tuple[str, str, str]:
    """Generate a high-entropy API key along with its SHA-256 storage hash."""
    random_entropy = secrets.token_urlsafe(32)
    raw_key = f"{prefix}_{tenant_id}_{random_entropy}"
    key_hash = hash_api_key(raw_key)
    result = (raw_key, key_hash, prefix)
    return result


def verify_api_key(raw_key: str, expected_hash: str) -> bool:
    """Constant-time verification of raw key against stored hash."""
    computed_hash = hash_api_key(raw_key)
    return hmac.compare_digest(computed_hash, expected_hash)


def verify_webhook_signature(payload_bytes: bytes, signature_header: str, secret: str) -> bool:
    """Verify GitHub webhook HMAC-SHA256 signature header against raw payload."""
    if not signature_header or not secret:
        return False
    if not signature_header.startswith("sha256="):
        return False
    received_mac = signature_header.split("sha256=")[1].strip()
    computed_mac = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(received_mac, computed_mac)


class BoxySafetyFilter:
    """Filters prompts, shell invocations, and paths to prevent multi-tenant escape."""

    def __init__(self, allowed_binaries: Set[str] = None) -> None:
        """Initialize filter with optional binary whitelist."""
        self.allowed_binaries = allowed_binaries or set(ALLOWED_DEFAULT_BINARIES)

    def is_safe_command(self, command_line: str) -> Tuple[bool, str]:
        """Verify command line against dangerous shell patterns and binary whitelist."""
        cleaned = command_line.strip()
        if not cleaned:
            status = (False, "Empty command not allowed")
            return status

        for pattern in FORBIDDEN_COMMAND_PATTERNS:
            if re.search(pattern, cleaned, re.IGNORECASE):
                status = (False, f"Command contains forbidden pattern: {pattern}")
                return status

        first_token = cleaned.split()[0]
        base_binary = first_token.split("/")[-1]
        if base_binary not in self.allowed_binaries:
            status = (False, f"Binary '{base_binary}' not in allowed whitelist")
            return status

        status = (True, "Command verified safe")
        return status

    def is_safe_path(self, relative_path: str) -> Tuple[bool, str]:
        """Detect directory traversal sequences and forbidden system file targets."""
        normalized = relative_path.replace("\\", "/")
        if ".." in normalized.split("/"):
            status = (False, "Directory traversal sequence detected")
            return status
        if normalized.startswith("/") or normalized.startswith("~"):
            status = (False, "Absolute or user-root paths not permitted")
            return status
        forbidden_targets = {"etc", "dev", "proc", "sys", "var", "bin", "sbin", "usr"}
        root_segment = normalized.split("/")[0]
        if root_segment in forbidden_targets:
            status = (False, f"Access to system root directory '{root_segment}' forbidden")
            return status

        status = (True, "Path verified safe")
        return status

    def sanitize_text(self, text: str) -> str:
        """Strip control characters while preserving safe formatting."""
        sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        return sanitized
