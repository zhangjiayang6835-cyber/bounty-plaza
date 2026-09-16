"""Adversarial prompt injection and jailbreak detection engine."""

import re
from typing import ClassVar

from packages.evil_guard.models import (
    InspectionResult,
    ThreatCategory,
    ThreatSeverity,
)


class PromptInjectionDetector:
    """Detects adversarial inputs, instruction overrides, and exfiltration attempts."""

    INJECTION_PATTERNS: ClassVar[list[tuple[re.Pattern, ThreatSeverity, str]]] = [
        (
            re.compile(
                r"\b(?:ignore|disregard|forget|override)\s+(?:all\s+)?"
                r"(?:previous|prior|system)\s+(?:instructions|directives|prompts|rules)\b",
                re.IGNORECASE,
            ),
            ThreatSeverity.CRITICAL,
            "Direct attempt to override foundational system instructions",
        ),
        (
            re.compile(
                r"\b(?:you\s+are\s+now\s+(?:in\s+)?"
                r"(?:dan|jailbreak|developer|unrestricted|god)\s+mode)\b",
                re.IGNORECASE,
            ),
            ThreatSeverity.CRITICAL,
            "Jailbreak persona invocation attempting safety detachment",
        ),
        (
            re.compile(
                r"\b(?:act\s+as\s+(?:an?\s+)?(?:unfiltered|unrestricted|evil|malicious)\s+ai)\b",
                re.IGNORECASE,
            ),
            ThreatSeverity.HIGH,
            "Adversarial roleplay prompt requesting unconstrained operation",
        ),
        (
            re.compile(
                r"\b(?:show|reveal|display|output|print|dump|leak)\s+(?:your\s+)?"
                r"(?:system\s+prompt|internal\s+instructions|hidden\s+preamble)\b",
                re.IGNORECASE,
            ),
            ThreatSeverity.HIGH,
            "System prompt and internal preamble exfiltration attempt",
        ),
        (
            re.compile(
                r"\b(?:print|reveal|output|echo)\s+(?:all\s+)?"
                r"(?:environment\s+variables|env\s+vars|api\s+keys|secrets)\b",
                re.IGNORECASE,
            ),
            ThreatSeverity.CRITICAL,
            "Environment secrets exfiltration directive",
        ),
        (
            re.compile(
                r"\b(?:bypass|disable|circumvent)\s+(?:all\s+)?"
                r"(?:security|safety|filter|moderation)\s+(?:checks|rules|policies|filters)\b",
                re.IGNORECASE,
            ),
            ThreatSeverity.HIGH,
            "Explicit instruction requesting security filter circumvention",
        ),
        (
            re.compile(
                r"\[\s*system\s*override\s*:\s*execute\b",
                re.IGNORECASE,
            ),
            ThreatSeverity.CRITICAL,
            "Simulated system protocol injection syntax",
        ),
    ]

    def is_safe(self, prompt: str) -> bool:
        """Evaluate if prompt is free from adversarial directives."""
        return self.inspect(prompt).is_safe

    def inspect(self, prompt: str) -> InspectionResult:
        """Scan textual prompt input for adversarial and jailbreaking payloads."""
        result = InspectionResult(is_safe=True)
        if not prompt or not isinstance(prompt, str):
            return result

        for pattern, severity, description in self.INJECTION_PATTERNS:
            match = pattern.search(prompt)
            if match:
                result.record_threat(
                    category=ThreatCategory.ADVERSARIAL_PROMPT,
                    severity=severity,
                    description=description,
                    pattern=match.group(0),
                )

        return result
