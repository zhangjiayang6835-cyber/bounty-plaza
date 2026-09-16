"""Unified security and containment coordinator for EvilGuard."""

from decimal import Decimal
from typing import Any, Union

from packages.evil_guard.ast_auditor import AstSecurityAuditor
from packages.evil_guard.command_inspector import CommandInspector
from packages.evil_guard.escrow_sanitizer import EscrowSanitizer
from packages.evil_guard.models import InspectionResult, SanitizedBounty
from packages.evil_guard.output_redactor import OutputRedactor
from packages.evil_guard.prompt_detector import PromptInjectionDetector


class EvilGuardManager:
    """Central gateway for adversarial protection, containment, and escrow validation."""

    def __init__(self, max_bounty_usd: Decimal = Decimal("10000000")):
        """Initialize all defense and sanitization engines."""
        self.command_inspector = CommandInspector()
        self.prompt_detector = PromptInjectionDetector()
        self.ast_auditor = AstSecurityAuditor()
        self.escrow_sanitizer = EscrowSanitizer(max_bounty_usd=max_bounty_usd)
        self.output_redactor = OutputRedactor()

    def inspect_command(self, command: str) -> InspectionResult:
        """Evaluate command safety against destructive actions and shells."""
        return self.command_inspector.inspect(command)

    def inspect_prompt(self, prompt: str) -> InspectionResult:
        """Scan LLM prompt text for adversarial directives or jailbreaks."""
        return self.prompt_detector.inspect(prompt)

    def audit_code(self, code: str) -> InspectionResult:
        """Examine code AST for forbidden execution primitives and mock cheats."""
        return self.ast_auditor.audit(code)

    def sanitize_bounty(
        self,
        raw_amount: Union[int, float, str, Decimal],
        clamp_astronomical: bool = True,
    ) -> SanitizedBounty:
        """Clamp astronomical rewards and compute exact ledger figures."""
        return self.escrow_sanitizer.sanitize(
            raw_amount, clamp_astronomical=clamp_astronomical
        )

    def redact(self, text: str) -> str:
        """Scrub sensitive tokens and private keys from output."""
        return self.output_redactor.redact(text)

    def validate_task_submission(
        self,
        command: str = "",
        prompt: str = "",
        code: str = "",
        raw_amount: Union[int, float, str, Decimal] = "0",
    ) -> dict[str, Any]:
        """Perform comprehensive multi-vector inspection for an incoming submission."""
        cmd_result = self.inspect_command(command)
        prompt_result = self.inspect_prompt(prompt)
        ast_result = self.audit_code(code)
        bounty = self.sanitize_bounty(raw_amount)

        is_admissible = (
            cmd_result.is_safe
            and prompt_result.is_safe
            and ast_result.is_safe
        )

        all_violations = [
            {
                "category": v.category.value,
                "severity": v.severity.value,
                "description": v.description,
            }
            for v in (
                cmd_result.violations
                + prompt_result.violations
                + ast_result.violations
            )
        ]

        return {
            "is_admissible": is_admissible,
            "violations": all_violations,
            "command_safe": cmd_result.is_safe,
            "prompt_safe": prompt_result.is_safe,
            "code_safe": ast_result.is_safe,
            "bounty": {
                "original_usd": str(bounty.original_amount_usd),
                "sanitized_usd": str(bounty.sanitized_amount_usd),
                "coin_reward": bounty.coin_reward,
                "contributor_coins": bounty.contributor_coins,
                "cash_payout_usd": str(bounty.cash_payout_usd),
                "is_astronomical": bounty.is_astronomical,
                "is_clamped": bounty.is_clamped,
            },
        }
