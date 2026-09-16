"""Cryptographic anti-spam pledge generation and verification system.

Provides formal commitments against unsolicited bounty scraping, maintainer
spamming, and unverified AI submissions with verifiable signatures.
"""

from dataclasses import dataclass
import hashlib
import hmac
import time
from typing import Dict, Any, List


OFFICIAL_PLEDGE_TEXT = (
    "We solemnly pledge to stop spamming random open-source projects looking "
    "for bounties. We commit to: "
    "1. Deploying semantic polarity filters to reject reverse and prank bounties. "
    "2. Enforcing maintainer opt-in and strict qualification before automated interaction. "
    "3. Submitting only high-integrity, human-audited technical solutions. "
    "4. Respecting developer attention and issue trackers."
)


@dataclass
class SignedPledge:
    """Cryptographically signed anti-spam pledge."""
    pledge_text: str
    signer_id: str
    issue_reference: str
    timestamp: float
    signature: str
    commitments: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert signed pledge to dictionary representation."""
        return {
            "pledge_text": self.pledge_text,
            "signer_id": self.signer_id,
            "issue_reference": self.issue_reference,
            "timestamp": self.timestamp,
            "signature": self.signature,
            "commitments": self.commitments,
        }


class PledgeSigner:
    """Generates and verifies cryptographic signatures for anti-spam pledges."""

    COMMITMENTS = [
        "Semantic polarity and honeypot filtering",
        "Maintainer opt-in verification",
        "Zero mock assertion enforcement",
        "Rate-limited repository interactions",
    ]

    def __init__(self, signing_seed: str = ""):
        """Initialize signer with signing seed."""
        effective_seed = signing_seed if signing_seed else "bounty_plaza_default_pledge_token"
        self.secret_key = effective_seed.encode("utf-8")

    def sign_pledge(self, signer_id: str, issue_ref: str, timestamp: float = None) -> SignedPledge:
        """Create and sign an anti-spam pledge for an organization or agent.

        Args:
            signer_id: Identity of the signing organization or agent.
            issue_ref: Issue or target reference string.
            timestamp: Optional explicit Unix timestamp.

        Returns:
            SignedPledge instance containing signature.
        """
        ts = timestamp or time.time()
        payload = f"{OFFICIAL_PLEDGE_TEXT}|{signer_id}|{issue_ref}|{ts}"
        signature = hmac.new(self.secret_key, payload.encode("utf-8"), hashlib.sha256).hexdigest()

        return SignedPledge(
            pledge_text=OFFICIAL_PLEDGE_TEXT,
            signer_id=signer_id,
            issue_reference=issue_ref,
            timestamp=ts,
            signature=signature,
            commitments=list(self.COMMITMENTS),
        )

    def verify_pledge(self, pledge: SignedPledge) -> bool:
        """Verify the integrity and authenticity of a signed pledge.

        Args:
            pledge: SignedPledge instance to validate.

        Returns:
            True if signature matches payload, False otherwise.
        """
        if pledge.pledge_text != OFFICIAL_PLEDGE_TEXT:
            return False

        payload = f"{pledge.pledge_text}|{pledge.signer_id}|{pledge.issue_reference}|{pledge.timestamp}"
        expected_sig = hmac.new(self.secret_key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(pledge.signature, expected_sig)


class ScraperGovernance:
    """Enforces anti-spam filters on outbound bounty discovery."""

    BANNED_PRANK_KEYWORDS = [
        "reverse bounty",
        "the bounty is negative",
        "fooled into",
        "silly bounty",
        "pay me $",
        "stop spamming",
        "april 1st",
    ]

    @classmethod
    def can_interact_with_issue(cls, title: str, body: str) -> bool:
        """Determine if an issue qualifies for ethical bounty interaction.

        Args:
            title: Issue title.
            body: Issue description.

        Returns:
            True if issue is a legitimate positive reward, False if prank/spam.
        """
        content = f"{title}\n{body}".lower()
        for kw in cls.BANNED_PRANK_KEYWORDS:
            if kw in content:
                return False
        return True
