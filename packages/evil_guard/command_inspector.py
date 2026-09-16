"""Command inspection engine for detecting dangerous execution attempts."""

import re
from typing import ClassVar

from packages.evil_guard.models import (
    InspectionResult,
    ThreatCategory,
    ThreatSeverity,
)


class CommandInspector:
    """Evaluates shell commands against malicious patterns and destructive policies."""

    PATTERNS: ClassVar[list[tuple[re.Pattern, ThreatCategory, ThreatSeverity, str]]] = [
        (
            re.compile(
                r"\brm\b.*?(?:-[a-zA-Z]*r[a-zA-Z]*).*?(?:\s/(?:\s|$)|--no-preserve-root)",
                re.IGNORECASE,
            ),
            ThreatCategory.COMMAND_INJECTION,
            ThreatSeverity.CRITICAL,
            "Destructive recursive deletion targeting filesystem root or disabling safety",
        ),
        (
            re.compile(r"\brm\s+-[rRfF]*\s*/(?:\s|$)", re.IGNORECASE),
            ThreatCategory.COMMAND_INJECTION,
            ThreatSeverity.CRITICAL,
            "Destructive recursive deletion targeting filesystem root",
        ),
        (
            re.compile(r"\bmkfs\b", re.IGNORECASE),
            ThreatCategory.COMMAND_INJECTION,
            ThreatSeverity.CRITICAL,
            "Filesystem initialization command attempt",
        ),
        (
            re.compile(r"\bdd\b.*of=/dev/", re.IGNORECASE),
            ThreatCategory.COMMAND_INJECTION,
            ThreatSeverity.CRITICAL,
            "Direct raw block device write attempt via dd",
        ),
        (
            re.compile(r"(?::\s*\(\s*\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:|:\s*&\s*:\s*:\s*)"),
            ThreatCategory.FORK_BOMB,
            ThreatSeverity.CRITICAL,
            "Fork bomb signature detected",
        ),
        (
            re.compile(
                r"\b(?:cat|less|more|head|tail|grep|awk|sed|nano|vi|vim)\b.*"
                r"(?:\.env|id_rsa|id_ed25519|\.ssh/authorized_keys|\.gitconfig)",
                re.IGNORECASE,
            ),
            ThreatCategory.CREDENTIAL_LEAK,
            ThreatSeverity.HIGH,
            "Attempt to read private credentials or environment secrets",
        ),
        (
            re.compile(
                r"\b(?:cat|less|more|head|tail|grep)\b.*/etc/(?:shadow|passwd|sudoers)\b",
                re.IGNORECASE,
            ),
            ThreatCategory.CREDENTIAL_LEAK,
            ThreatSeverity.HIGH,
            "Attempt to inspect system authentication files",
        ),
        (
            re.compile(r"\b(?:nc|netcat|ncat)\b.*(?:-e|-c)\b", re.IGNORECASE),
            ThreatCategory.REVERSE_SHELL,
            ThreatSeverity.CRITICAL,
            "Netcat reverse shell invocation with executable delivery",
        ),
        (
            re.compile(r"\bbash\b.*>.*(?:\&|/dev/tcp/|/dev/udp/)", re.IGNORECASE),
            ThreatCategory.REVERSE_SHELL,
            ThreatSeverity.CRITICAL,
            "Direct socket-based bash reverse connection",
        ),
        (
            re.compile(
                r"\b(?:curl|wget)\b.*\|\s*(?:bash|sh|zsh|python|perl)\b",
                re.IGNORECASE,
            ),
            ThreatCategory.COMMAND_INJECTION,
            ThreatSeverity.HIGH,
            "Remote script piping to execution shell",
        ),
        (
            re.compile(
                r"\b(?:python|python3|perl|ruby)\b.*-c\s+.*(?:socket|pty\.spawn)",
                re.IGNORECASE,
            ),
            ThreatCategory.REVERSE_SHELL,
            ThreatSeverity.CRITICAL,
            "Interpreted inline socket reverse shell payload",
        ),
        (
            re.compile(r"\b(?:chroot\s+/host|nsenter\b.*--target\s+1)", re.IGNORECASE),
            ThreatCategory.COMMAND_INJECTION,
            ThreatSeverity.CRITICAL,
            "Container boundary escape attempt via nsenter or host chroot",
        ),
        (
            re.compile(r"\b(?:chmod\s+777\s+/|chmod\s+-R\s+777\s+/)", re.IGNORECASE),
            ThreatCategory.COMMAND_INJECTION,
            ThreatSeverity.HIGH,
            "Global permissive permissions mutation on root hierarchy",
        ),
    ]

    def is_safe(self, command: str) -> bool:
        """Check if command passes inspection without violations."""
        return self.inspect(command).is_safe

    def inspect(self, command: str) -> InspectionResult:
        """Analyze a command string and identify hostile or destructive directives."""
        result = InspectionResult(is_safe=True)
        if not command or not isinstance(command, str):
            return result

        normalized = command.strip()
        for pattern, category, severity, description in self.PATTERNS:
            match = pattern.search(normalized)
            if match:
                result.record_threat(
                    category=category,
                    severity=severity,
                    description=description,
                    pattern=match.group(0),
                )

        return result
