"""Security models and telemetry data structures for EvilGuard."""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class ThreatSeverity(str, Enum):
    """Severity ratings for detected security threats."""

    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ThreatCategory(str, Enum):
    """Categorization of hostile security behaviors."""

    COMMAND_INJECTION = "COMMAND_INJECTION"
    REVERSE_SHELL = "REVERSE_SHELL"
    CREDENTIAL_LEAK = "CREDENTIAL_LEAK"
    FORK_BOMB = "FORK_BOMB"
    ADVERSARIAL_PROMPT = "ADVERSARIAL_PROMPT"
    SYSTEM_OVERRIDE = "SYSTEM_OVERRIDE"
    ARITHMETIC_OVERFLOW = "ARITHMETIC_OVERFLOW"
    AST_VIOLATION = "AST_VIOLATION"


@dataclass
class SecurityViolation:
    """Detailed record of an identified policy or security violation."""

    category: ThreatCategory
    severity: ThreatSeverity
    description: str
    matched_pattern: str = ""


@dataclass
class InspectionResult:
    """Result of an inspection pass across commands, prompts, or code."""

    is_safe: bool
    violations: list[SecurityViolation] = field(default_factory=list)
    highest_severity: ThreatSeverity = ThreatSeverity.NONE
    sanitized_output: str = ""

    def add_violation(self, violation: SecurityViolation) -> None:
        """Register a violation and escalate severity if necessary."""
        self.violations.append(violation)
        self.is_safe = False
        severity_ranks = {
            ThreatSeverity.NONE: 0,
            ThreatSeverity.LOW: 1,
            ThreatSeverity.MEDIUM: 2,
            ThreatSeverity.HIGH: 3,
            ThreatSeverity.CRITICAL: 4,
        }
        if severity_ranks[violation.severity] > severity_ranks[self.highest_severity]:
            self.highest_severity = violation.severity

    def record_threat(
        self,
        category: ThreatCategory,
        severity: ThreatSeverity,
        description: str,
        pattern: str,
    ) -> None:
        """Create and append a new violation entry."""
        entry = SecurityViolation(
            category=category,
            severity=severity,
            description=description,
            matched_pattern=pattern,
        )
        self.add_violation(entry)


@dataclass
class BountyPayoutBreakdown:
    """Financial breakdown and participant allocations for a bounty."""

    contributor_ratio: Decimal
    contributor_coins: int
    cash_payout_usd: Decimal


@dataclass
class SanitizedBounty:
    """Sanitized and mathematically verified bounty reward metrics."""

    original_amount_usd: Decimal
    sanitized_amount_usd: Decimal
    coin_reward: int
    payout: BountyPayoutBreakdown
    is_astronomical: bool
    is_clamped: bool
    status_note: str

    @property
    def contributor_ratio(self) -> Decimal:
        """Contributor payout ratio helper."""
        return self.payout.contributor_ratio

    @property
    def contributor_coins(self) -> int:
        """Contributor coin allocation helper."""
        return self.payout.contributor_coins

    @property
    def cash_payout_usd(self) -> Decimal:
        """Calculated cash payout in USD helper."""
        return self.payout.cash_payout_usd
