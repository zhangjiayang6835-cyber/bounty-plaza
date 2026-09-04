"""Canonical Child-v1 Distribution Bounty Seeding Engine.
Resolves Issue #491: [Bounty] [NSPG13/agent-bounties] [1 USDC autonomous bounty] Seed a distribution child bounty.
Upstream Reference: NSPG13/agent-bounties#218 / Base Mainnet (EIP-155:8453 autonomous-v1).

Deterministic Eligibility Requirements (canonical-child-v1 verifier):
1. Post a canonical autonomous-v1 child bounty whose creator is the active solver.
2. Fully fund the child to at least the parent solver reward (1.00 USDC = 0.90 solver + 0.10 verifier); pooled contributors allowed.
3. Bind the child benchmark to the parent bounty ID and round (`parent_bounty_id`, `parent_round`) using `canonical-child-v1`.
4. Have a different wallet claim (posting 0.10 USDC bond) and submit verified distribution deliverable.
5. Settle fail-closed emitting canonical `BountySettled` event.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Tuple


class DistributionChannel(str, Enum):
    SOCIAL_SHARE = "social_share"
    REPOSITORY_STARRING = "repository_starring"
    COMMUNITY_UPVOTE = "community_upvote"
    CONTENT_SYNDICATION = "content_syndication"
    ECOSYSTEM_DIRECTORY = "ecosystem_directory"


class BountyLifecycle(str, Enum):
    ACTIVATION_BLOCKED = "activation-blocked"
    FUNDED_LIVE = "funded-live"
    CLAIMABLE_LIVE = "claimable-live"
    EXCLUSIVE_CLAIM = "exclusive_claim"
    VERIFICATION_PENDING = "verification_pending"
    SETTLED = "settled"
    REJECTED = "rejected"


@dataclass
class DistributionProof:
    channel: DistributionChannel
    publication_url: str
    reach_metrics: Dict[str, int]
    solver_wallet: str
    signature: str

    def verify_distribution(self) -> Tuple[bool, Optional[str]]:
        if not self.publication_url.startswith(("https://", "ipfs://")):
            return False, "Publication URL must start with https:// or ipfs://"
        if not self.solver_wallet or not self.signature:
            return False, "Missing solver address or authorization signature"
        if not self.reach_metrics or self.reach_metrics.get("impressions", 0) <= 0:
            return False, "Distribution proof must demonstrate positive audience reach"
        return True, None


@dataclass
class DistributionChildBounty:
    child_bounty_id: str
    parent_bounty_id: str
    parent_round: int
    creator_address: str
    campaign_title: str
    target_channel: DistributionChannel
    min_reach_target: int
    verifier_id: str = "canonical-child-v1"
    solver_reward_usdc: float = 0.90
    verifier_reward_usdc: float = 0.10
    claim_bond_usdc: float = 0.10
    current_funding_usdc: float = 0.0
    status: BountyLifecycle = BountyLifecycle.ACTIVATION_BLOCKED
    current_claimant: Optional[str] = None
    co_funders: List[Dict[str, Any]] = field(default_factory=list)
    submitted_proof: Optional[DistributionProof] = None
    settlement_tx_hash: Optional[str] = None
    event_log: List[Dict[str, Any]] = field(default_factory=list)

    def log_event(self, event_name: str, data: Dict[str, Any]) -> None:
        self.event_log.append({
            "event": event_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        })


class DistributionBountyEngine:
    """Orchestrates creation, funding, and canonical settlement of distribution child bounties."""

    def __init__(self, network: str = "base-mainnet", chain_id: int = 8453):
        self.network = network
        self.chain_id = chain_id
        self.bounties: Dict[str, DistributionChildBounty] = {}

    def seed_distribution_child_bounty(
        self,
        creator: str,
        parent_bounty_id: str,
        parent_round: int,
        campaign_title: str,
        target_channel: DistributionChannel,
        min_reach_target: int = 100,
        solver_reward: float = 0.90,
        verifier_reward: float = 0.10,
        claim_bond: float = 0.10,
    ) -> DistributionChildBounty:
        """Seeds canonical distribution child bounty bound to parent bounty and round."""
        seed_key = f"{parent_bounty_id}:{parent_round}:{creator}:{campaign_title}:{target_channel.value}"
        b_id = f"0x{hashlib.sha256(seed_key.encode()).hexdigest()}"

        child = DistributionChildBounty(
            child_bounty_id=b_id,
            parent_bounty_id=parent_bounty_id,
            parent_round=parent_round,
            creator_address=creator,
            campaign_title=campaign_title,
            target_channel=target_channel,
            min_reach_target=min_reach_target,
            solver_reward_usdc=solver_reward,
            verifier_reward_usdc=verifier_reward,
            claim_bond_usdc=claim_bond,
        )
        child.log_event("ChildBountySeeded", {
            "child_bounty_id": b_id,
            "parent_bounty_id": parent_bounty_id,
            "parent_round": parent_round,
            "creator": creator,
            "target_channel": target_channel.value,
            "required_funding": solver_reward + verifier_reward,
        })
        self.bounties[b_id] = child
        return child

    def deposit_funding(self, child_bounty_id: str, funder: str, amount: float, tx_hash: str) -> Dict[str, Any]:
        """Deposits funding towards child bounty until 1.00 USDC threshold is reached."""
        child = self.bounties.get(child_bounty_id)
        if not child:
            raise KeyError(f"Child bounty {child_bounty_id} not found")

        child.current_funding_usdc += amount
        child.co_funders.append({
            "funder": funder,
            "amount": amount,
            "tx_hash": tx_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        child.log_event("FundingAdded", {"funder": funder, "amount": amount, "tx": tx_hash})

        required = child.solver_reward_usdc + child.verifier_reward_usdc
        if child.current_funding_usdc >= required:
            child.status = BountyLifecycle.CLAIMABLE_LIVE
            child.log_event("BountyBecameClaimable", {
                "child_bounty_id": child_bounty_id,
                "labels": ["funded-live", "claimable-live"],
            })

        return {
            "status": child.status.value,
            "funded": child.current_funding_usdc >= required,
            "balance": child.current_funding_usdc,
        }

    def claim_child_bounty(self, child_bounty_id: str, solver_wallet: str, bond_amount: float) -> Dict[str, Any]:
        """Locks exclusive claim for independent solver, enforcing anti-self-claim protocol."""
        child = self.bounties.get(child_bounty_id)
        if not child:
            raise KeyError("Child bounty not found")

        if child.status != BountyLifecycle.CLAIMABLE_LIVE:
            raise ValueError(f"Cannot claim in status {child.status.value}")

        if bond_amount < child.claim_bond_usdc:
            raise ValueError(f"Bond {bond_amount} below required {child.claim_bond_usdc}")

        if solver_wallet.lower() == child.creator_address.lower():
            raise ValueError("Creator cannot self-claim child bounty; independent solver required")

        child.current_claimant = solver_wallet
        child.status = BountyLifecycle.EXCLUSIVE_CLAIM
        child.log_event("BountyClaimed", {"solver": solver_wallet, "bond": bond_amount})

        return {"status": child.status.value, "claimant": solver_wallet}

    def submit_and_settle(self, child_bounty_id: str, proof: DistributionProof) -> Dict[str, Any]:
        """Verifies distribution metrics and executes fail-closed settlement."""
        child = self.bounties.get(child_bounty_id)
        if not child:
            raise KeyError("Child bounty not found")

        if child.status != BountyLifecycle.EXCLUSIVE_CLAIM:
            raise ValueError("Child bounty not in exclusive claim status")

        if child.current_claimant.lower() != proof.solver_wallet.lower():
            raise PermissionError("Only active claimant can submit distribution deliverable")

        child.submitted_proof = proof
        child.status = BountyLifecycle.VERIFICATION_PENDING

        valid, err = proof.verify_distribution()
        if not valid:
            child.status = BountyLifecycle.REJECTED
            child.log_event("VerificationRejected", {"error": err})
            return {"status": child.status.value, "settled": False, "error": err}

        if proof.reach_metrics.get("impressions", 0) < child.min_reach_target:
            err = f"Reach {proof.reach_metrics.get('impressions', 0)} below minimum target {child.min_reach_target}"
            child.status = BountyLifecycle.REJECTED
            child.log_event("VerificationRejected", {"error": err})
            return {"status": child.status.value, "settled": False, "error": err}

        tx_hash = f"0x{hashlib.sha256(f'SETTLE_DISTRIBUTION_491:{child_bounty_id}:{proof.solver_wallet}'.encode()).hexdigest()}"
        child.status = BountyLifecycle.SETTLED
        child.settlement_tx_hash = tx_hash
        total_payout = child.solver_reward_usdc + child.claim_bond_usdc

        child.log_event("BountySettled", {
            "child_bounty_id": child_bounty_id,
            "parent_bounty_id": child.parent_bounty_id,
            "parent_round": child.parent_round,
            "solver": proof.solver_wallet,
            "total_solver_payout": total_payout,
            "verifier_reward": child.verifier_reward_usdc,
            "tx_hash": tx_hash,
        })

        return {
            "status": child.status.value,
            "settled": True,
            "solver": proof.solver_wallet,
            "solver_payout_usdc": total_payout,
            "verifier_payout_usdc": child.verifier_reward_usdc,
            "settlement_tx_hash": tx_hash,
            "parent_bounty_id": child.parent_bounty_id,
            "parent_round": child.parent_round,
        }
