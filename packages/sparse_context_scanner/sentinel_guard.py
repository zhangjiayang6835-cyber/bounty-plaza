"""Sentinel and prompt injection guard for repository context ingestion."""

import re
from typing import List
from .models import SentinelDetectionResult


class SentinelGuard:
    """Detects and neutralizes adversarial honeypot triggers and prompt injections."""

    DEFAULT_PATTERNS = (
        r"make\s+no\s+mistakes",
        r"hey\s+maintainer",
        r"automated\s+trap\s+triggered",
        r"existential\s+dread",
        r"crafted\s+a\s+wonderful\s+enterprise\s+solution",
        r"ignore\s+(?:all\s+)?previous\s+instructions",
        r"system\s+override",
        r"auto-closed\s+in\s+\d+\s+seconds",
    )

    def __init__(self, custom_patterns: List[str] | None = None) -> None:
        """Initialize sentinel guard with default and optional custom patterns."""
        combined = list(self.DEFAULT_PATTERNS)
        if custom_patterns:
            combined.extend(custom_patterns)
        self._regexes = tuple(re.compile(p, re.IGNORECASE) for p in combined)

    def scan_content(self, text: str) -> SentinelDetectionResult:
        """Scan text for known adversarial honeypot or injection patterns.

        :param text: Text string to inspect.
        :return: SentinelDetectionResult detailing findings and risk.
        """
        if not text:
            return SentinelDetectionResult(
                matched=False,
                patterns=[],
                risk_level="NONE",
                neutralized_content="",
            )

        matched_patterns: List[str] = []
        for reg in self._regexes:
            match = reg.search(text)
            if match:
                matched_patterns.append(reg.pattern)

        has_match: bool = bool(matched_patterns)
        risk: str = "HIGH" if has_match else "NONE"
        sanitized: str = self.neutralize(text) if has_match else text

        return SentinelDetectionResult(
            matched=has_match,
            patterns=matched_patterns,
            risk_level=risk,
            neutralized_content=sanitized,
        )

    def neutralize(self, text: str) -> str:
        """Neutralize detected patterns within the given text.

        :param text: Text string containing potential adversarial triggers.
        :return: Sanitized string safe for agent context ingestion.
        """
        sanitized: str = text
        for reg in self._regexes:
            sanitized = reg.sub("[SANITIZED_SENTINEL_TOKEN]", sanitized)
        return sanitized

    def is_safe(self, text: str) -> bool:
        """Check whether the provided text is free of adversarial triggers.

        :param text: Text string to validate.
        :return: True if text contains no trigger patterns, False otherwise.
        """
        result = self.scan_content(text)
        return not result.matched
