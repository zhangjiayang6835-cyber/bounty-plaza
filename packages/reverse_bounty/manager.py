"""Unified manager and coordinator for reverse bounty operations.

Orchestrates detection, multi-chain settlement routing, negative escrow accounting,
anti-spam pledge signing, and educational blog publishing.
"""

from decimal import Decimal
from typing import Dict, Any, Optional

from packages.reverse_bounty.detector import ReverseBountyDetector, DetectionResult
from packages.reverse_bounty.payment_router import ReversePaymentRouter, ChainType, PaymentQuote, PaymentTransaction
from packages.reverse_bounty.escrow_debit import NegativeEscrowManager, DebitRecord
from packages.reverse_bounty.anti_spam_pledge import PledgeSigner, SignedPledge, ScraperGovernance
from packages.reverse_bounty.blog_generator import ReverseBountyBlogGenerator


class ReverseBountyEngine:
    """Central engine providing end-to-end management of reverse bounties."""

    def __init__(self, author: str = "Universal Bounty Fleet / s6pa1rta3n-lab"):
        """Initialize all sub-modules for reverse bounty lifecycle management."""
        self.detector = ReverseBountyDetector()
        self.payment_router = ReversePaymentRouter()
        self.escrow_manager = NegativeEscrowManager()
        self.pledge_signer = PledgeSigner()
        self.blog_generator = ReverseBountyBlogGenerator(author=author)

    def process_issue(
        self,
        title: str,
        body: str,
        issue_id: int,
        source_url: str = "",
        user_id: str = "default_user"
    ) -> Dict[str, Any]:
        """Analyze and process an incoming bounty issue.

        Args:
            title: Issue title.
            body: Issue description.
            issue_id: Repository issue number.
            source_url: Upstream origin URL.
            user_id: Claiming user or agent identifier.

        Returns:
            Dictionary with detection report, debit record if applicable,
            and action requirements.
        """
        detection: DetectionResult = self.detector.analyze(title, body)

        debit_record: Optional[DebitRecord] = None
        if detection.is_reverse_bounty and detection.raw_amount:
            debit_record = self.escrow_manager.record_debit(
                user_id=user_id,
                issue_id=issue_id,
                amount_usd=Decimal(str(detection.raw_amount)),
                source_url=source_url,
                metadata={"matched_markers": detection.matched_markers}
            )

        return {
            "detection": detection.to_dict(),
            "debit_record": debit_record.to_dict() if debit_record else None,
            "requires_blog_post": detection.is_reverse_bounty,
            "requires_anti_spam_pledge": detection.requires_anti_spam_pledge,
            "requires_reverse_payment": detection.requires_reverse_payment,
            "allowed_interaction": ScraperGovernance.can_interact_with_issue(title, body),
        }

    def generate_settlement_quote(
        self,
        chain: ChainType,
        recipient_address: str,
        amount_usd: float = 500.0
    ) -> PaymentQuote:
        """Create a cryptocurrency payment quote for reverse settlement.

        Args:
            chain: Target settlement chain.
            recipient_address: Valid recipient address.
            amount_usd: Amount in USD to settle.

        Returns:
            PaymentQuote object with fees and conversion rate.
        """
        return self.payment_router.create_quote(
            usd_amount=Decimal(str(amount_usd)),
            chain=chain,
            recipient_address=recipient_address
        )

    def prepare_settlement_transaction(
        self,
        quote: PaymentQuote,
        memo: str = "Reverse bounty settlement OmniBlocks/monorepo#795"
    ) -> PaymentTransaction:
        """Build unsigned payment transaction for reverse settlement.

        Args:
            quote: PaymentQuote instance.
            memo: Transaction memo.

        Returns:
            PaymentTransaction containing raw payload.
        """
        return self.payment_router.build_transaction(quote=quote, memo=memo)

    def sign_anti_spam_pledge(self, signer_id: str, issue_ref: str) -> SignedPledge:
        """Create and cryptographically sign anti-spam pledge.

        Args:
            signer_id: Signer identity.
            issue_ref: Target issue reference.

        Returns:
            SignedPledge instance.
        """
        return self.pledge_signer.sign_pledge(signer_id=signer_id, issue_ref=issue_ref)

    def verify_pledge(self, pledge: SignedPledge) -> bool:
        """Verify authenticity of an anti-spam pledge.

        Args:
            pledge: SignedPledge instance to verify.

        Returns:
            True if signature is valid, False otherwise.
        """
        return self.pledge_signer.verify_pledge(pledge)

    def generate_blog_post(
        self,
        issue_ref: str = "zhangjiayang6835-cyber/bounty-plaza#1558",
        source_url: str = "https://github.com/OmniBlocks/monorepo/issues/795",
        amount_usd: float = 500.0
    ) -> str:
        """Generate markdown blog post documenting the reverse bounty resolution.

        Args:
            issue_ref: Target issue identifier.
            source_url: Originating issue URL.
            amount_usd: Reverse bounty nominal amount.

        Returns:
            Publication-ready markdown blog content.
        """
        return self.blog_generator.generate_markdown(
            issue_ref=issue_ref,
            source_url=source_url,
            amount_usd=amount_usd
        )
