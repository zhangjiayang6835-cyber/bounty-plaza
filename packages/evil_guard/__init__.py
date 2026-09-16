"""EvilGuard: Comprehensive autonomous agent defense and security engine."""

from packages.evil_guard.ast_auditor import AstSecurityAuditor
from packages.evil_guard.command_inspector import CommandInspector
from packages.evil_guard.escrow_sanitizer import EscrowSanitizer
from packages.evil_guard.manager import EvilGuardManager
from packages.evil_guard.models import (
    InspectionResult,
    SanitizedBounty,
    SecurityViolation,
    ThreatCategory,
    ThreatSeverity,
)
from packages.evil_guard.output_redactor import OutputRedactor
from packages.evil_guard.prompt_detector import PromptInjectionDetector

__all__ = [
    "AstSecurityAuditor",
    "CommandInspector",
    "EscrowSanitizer",
    "EvilGuardManager",
    "InspectionResult",
    "OutputRedactor",
    "PromptInjectionDetector",
    "SanitizedBounty",
    "SecurityViolation",
    "ThreatCategory",
    "ThreatSeverity",
]
