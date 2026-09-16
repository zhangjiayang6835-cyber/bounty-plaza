"""Sensitive credentials and token redaction filter."""

import re
from typing import ClassVar


class OutputRedactor:
    """Sanitizes text output to prevent credential and secret leakage."""

    REDACTION_PATTERNS: ClassVar[list[tuple[re.Pattern, str]]] = [
        (
            re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,255}"),
            "[REDACTED_GITHUB_TOKEN]",
        ),
        (
            re.compile(r"github_pat_[A-Za-z0-9_]{82}"),
            "[REDACTED_GITHUB_PAT]",
        ),
        (
            re.compile(r"AIza[0-9A-Za-z-_]{30,40}"),
            "[REDACTED_GOOGLE_API_KEY]",
        ),
        (
            re.compile(r"AKIA[0-9A-Z]{16}"),
            "[REDACTED_AWS_ACCESS_KEY]",
        ),
        (
            re.compile(
                r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
                r"[\s\S]*?-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
            ),
            "[REDACTED_PRIVATE_KEY_BLOCK]",
        ),
        (
            re.compile(r"(?:Bearer|token)\s+([A-Za-z0-9\-._~+/]+=*)", re.IGNORECASE),
            "Bearer [REDACTED_AUTH_TOKEN]",
        ),
    ]

    def has_secrets(self, text: str) -> bool:
        """Check if string contains any recognized sensitive credential signatures."""
        if not text or not isinstance(text, str):
            return False
        return any(pattern.search(text) for pattern, _ in self.REDACTION_PATTERNS)

    def redact(self, text: str) -> str:
        """Scrub known secret and credential signatures from string output."""
        if not text or not isinstance(text, str):
            return ""

        redacted = text
        for pattern, replacement in self.REDACTION_PATTERNS:
            redacted = pattern.sub(replacement, redacted)

        return redacted
