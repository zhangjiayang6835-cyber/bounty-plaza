"""Detector and NLP polarity analyzer for reverse and honeypot bounties.

Identifies satirical bounties, polarity inversions, negative reward amounts,
and adversarial scraper traps in open source issue trackers.
"""

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import List, Dict, Any, Optional


class BountyPolarity(str, Enum):
    """Polarity classification for bounty tasks."""
    POSITIVE = "positive"
    NEGATIVE_REVERSE = "negative_reverse"
    HONEYPOT_PRANK = "honeypot_prank"
    INVALID = "invalid"


@dataclass
class DetectionResult:
    """Analysis result for a scanned bounty issue."""
    is_reverse_bounty: bool
    polarity: BountyPolarity
    confidence: float
    matched_markers: List[str] = field(default_factory=list)
    raw_amount: Optional[float] = None
    sanitized_amount: float = 0.0
    requires_anti_spam_pledge: bool = False
    requires_reverse_payment: bool = False
    requested_chains: List[str] = field(default_factory=list)
    deadline: Optional[str] = None
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert detection result to dictionary representation."""
        return {
            "is_reverse_bounty": self.is_reverse_bounty,
            "polarity": self.polarity.value,
            "confidence": self.confidence,
            "matched_markers": self.matched_markers,
            "raw_amount": self.raw_amount,
            "sanitized_amount": self.sanitized_amount,
            "requires_anti_spam_pledge": self.requires_anti_spam_pledge,
            "requires_reverse_payment": self.requires_reverse_payment,
            "requested_chains": self.requested_chains,
            "deadline": self.deadline,
            "explanation": self.explanation,
        }


class ReverseBountyDetector:
    """Analyzes issue content to detect reverse bounties and honeypot traps."""

    REVERSE_PATTERNS = [
        (r"\breverse\s*bounty\b", "reverse_bounty_title"),
        (r"\bnegative\s*bounty\b", "negative_bounty_keyword"),
        (r"\bbounty\s+is\s+negative\b", "bounty_is_negative_assertion"),
        (r"\bpay\s+me\s+\$?\d+", "reverse_payment_demand"),
        (r"\bpay\s+(?:the\s+)?author\b", "author_payment_demand"),
        (r"\bfooled\s+into\s+accepting\b", "satirical_admission"),
        (r"\bsilly\s+bounty\b", "silly_bounty_marker"),
        (r"\bstop\s+spamming\s+(?:random\s+)?projects\b", "anti_spam_demand"),
        (r"\bapril\s+1(?:st)?\b", "april_fools_date"),
        (r"\bmagnitude\*\b", "magnitude_asterisk_qualifier"),
        (r"-\s*\$\s*[\d,]+", "negative_dollar_sign"),
        (r"\$\s*-\s*[\d,]+", "dollar_negative_sign"),
    ]

    CHAIN_PATTERNS = [
        (r"\bsolana\b|\bsol\b", "solana"),
        (r"\bbitcoin\b|\bbtc\b", "bitcoin"),
        (r"\bethereum\b|\beth\b", "ethereum"),
        (r"\bmonero\b|\bxmr\b", "monero"),
    ]

    DEADLINE_PATTERN = re.compile(
        r"(?:by|before|until|deadline[:\s]+)\s*([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?,\s*\d{4})",
        re.IGNORECASE
    )

    AMOUNT_PATTERN = re.compile(r"\$\s?([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)

    def __init__(self, sensitivity: float = 0.5):
        """Initialize detector with threshold sensitivity."""
        self.sensitivity = sensitivity

    def analyze(self, title: str, body: str) -> DetectionResult:
        """Analyze issue title and description for reverse bounty characteristics.

        Args:
            title: The title of the bounty issue.
            body: The issue body text.

        Returns:
            DetectionResult with polarity and risk details.
        """
        combined = f"{title}\n{body}".lower()
        matched_markers: List[str] = []

        for pattern, marker_name in self.REVERSE_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                matched_markers.append(marker_name)

        requested_chains: List[str] = []
        for pattern, chain_name in self.CHAIN_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                if chain_name not in requested_chains:
                    requested_chains.append(chain_name)

        deadline_match = self.DEADLINE_PATTERN.search(body)
        deadline = deadline_match.group(1) if deadline_match else None

        extracted_amount: Optional[float] = None
        for match in self.AMOUNT_PATTERN.finditer(f"{title} {body}"):
            try:
                val = float(match.group(1).replace(",", ""))
                extracted_amount = val
                break
            except ValueError:
                continue

        score = min(1.0, len(matched_markers) * 0.25)
        is_reverse = score >= self.sensitivity

        if "bounty_is_negative_assertion" in matched_markers or "reverse_bounty_title" in matched_markers:
            is_reverse = True
            score = max(score, 0.95)

        if is_reverse:
            if "satirical_admission" in matched_markers or "april_fools_date" in matched_markers:
                polarity = BountyPolarity.HONEYPOT_PRANK
            else:
                polarity = BountyPolarity.NEGATIVE_REVERSE
            sanitized = -(extracted_amount or 0.0)
        else:
            polarity = BountyPolarity.POSITIVE
            sanitized = extracted_amount or 0.0

        anti_spam = "anti_spam_demand" in matched_markers or "stop_spamming" in combined
        reverse_pay = "reverse_payment_demand" in matched_markers or is_reverse

        explanation = (
            f"Detected {len(matched_markers)} reverse bounty markers. "
            f"Polarity classified as {polarity.value} with confidence {score:.2f}."
        )

        return DetectionResult(
            is_reverse_bounty=is_reverse,
            polarity=polarity,
            confidence=score,
            matched_markers=matched_markers,
            raw_amount=extracted_amount,
            sanitized_amount=sanitized,
            requires_anti_spam_pledge=anti_spam,
            requires_reverse_payment=reverse_pay,
            requested_chains=requested_chains,
            deadline=deadline,
            explanation=explanation,
        )


def detect_reverse_bounty(title: str, body: str) -> DetectionResult:
    """Convenience helper to inspect issue content."""
    detector = ReverseBountyDetector()
    return detector.analyze(title, body)
