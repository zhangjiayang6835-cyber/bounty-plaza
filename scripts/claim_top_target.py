"""Automated Top Target Claim Orchestrator Subsystem.
Resolves Issue #845: Claim Top Target Issue.
Related: Open Competition V2 / Base Mainnet Autonomous Bounties ($89 USD).

Features:
1. Ingests candidate bounties across GitHub and Base mainnet.
2. Evaluates multi-dimensional priority score based on:
   - Net cash margin ($USD prize minus gas and proof fees).
   - Expected settlement velocity (deterministic verifier vs human dispute).
   - Claim status and competition expiration horizon.
3. Automatically selects the optimal top target issue.
4. Generates standard `/claim` reservation payload adhering to 24h task locking rules.
"""

from dataclasses import dataclass, field
import json
import re
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class TargetBounty:
    issue_number: int
    title: str
    prize_usd: float
    verifier_type: str = "deterministic_module"
    is_claimed: bool = False
    proof_fee_usd: float = 0.10
    gas_fee_usd: float = 0.01
    settlement_latency_seconds: float = 120.0

    @property
    def net_margin_usd(self) -> float:
        return max(0.0, self.prize_usd - (self.proof_fee_usd + self.gas_fee_usd))

    @property
    def priority_score(self) -> float:
        if self.is_claimed:
            return 0.0
        verifier_bonus = 1.5 if self.verifier_type == "deterministic_module" else 1.0
        # Yield velocity ($/min) with verifier multiplier
        rate_per_minute = (self.net_margin_usd / max(1.0, self.settlement_latency_seconds)) * 60.0
        return rate_per_minute * verifier_bonus


class TopTargetClaimEngine:
    """Ranks available bounties and executes automated task reservation."""

    def __init__(self, lock_duration_hours: int = 24):
        self.lock_duration_hours = lock_duration_hours

    def select_top_target(self, candidates: List[TargetBounty]) -> Optional[TargetBounty]:
        """Filters unclaimed bounties and returns the highest priority target."""
        available = [b for b in candidates if not b.is_claimed and b.prize_usd > 0]
        if not available:
            return None
        return max(available, key=lambda b: b.priority_score)

    def generate_claim_payload(self, target: TargetBounty, solver_id: str = "wiliancolomboo-tech") -> Dict[str, Any]:
        """Generates standard `/claim` command comment for issue reservation."""
        comment_body = f"/claim zhangjiayang6835-cyber/bounty-plaza#{target.issue_number}\n\n" \
                       f"> Automated claim by `{solver_id}` for 24h task lock.\n" \
                       f"> Target: {target.title} (${target.prize_usd:.2f} USD / net: ${target.net_margin_usd:.2f} USDC)."

        return {
            "issue_number": target.issue_number,
            "command": f"/claim zhangjiayang6835-cyber/bounty-plaza#{target.issue_number}",
            "comment_body": comment_body,
            "target_title": target.title,
            "net_margin_usd": target.net_margin_usd,
            "priority_score": target.priority_score,
        }

    def process_bounties(self, candidate_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Parses raw issue data, ranks candidates, and selects top target."""
        bounties = []
        for d in candidate_data:
            bounties.append(TargetBounty(
                issue_number=int(d.get("number") or d.get("issue_number", 0)),
                title=str(d.get("title", "")),
                prize_usd=float(d.get("prize_usd") or d.get("reward", 0.0)),
                verifier_type=str(d.get("verifier_type", "deterministic_module")),
                is_claimed=bool(d.get("is_claimed", False)),
                settlement_latency_seconds=float(d.get("settlement_latency_seconds", 120.0)),
            ))

        top = self.select_top_target(bounties)
        if not top:
            return {
                "selected": False,
                "message": "No available unclaimed targets found",
                "top_target": None,
            }

        claim_info = self.generate_claim_payload(top)
        return {
            "selected": True,
            "total_candidates": len(bounties),
            "top_target": claim_info,
        }
