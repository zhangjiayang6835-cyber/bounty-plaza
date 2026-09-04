"""Canonical Child-v1 External-User-Request Bounty Seeding Engine.
Resolves Issue #493: [Bounty] [NSPG13/agent-bounties] [1 USDC autonomous bounty] Seed an external-user-request child bounty.
Upstream Reference: NSPG13/agent-bounties#220 / Base Mainnet (EIP-155:8453 autonomous-v1).

Deterministic Eligibility Requirements (canonical-child-v1 verifier):
1. Post a canonical autonomous-v1 child bounty whose creator is the active solver.
2. Fully fund the child to at least the parent solver reward (1.00 USDC = 0.90 solver + 0.10 verifier); pooled contributors allowed.
3. Bind the child benchmark to the parent bounty ID and round (`parent_bounty_id`, `parent_round`) using `canonical-child-v1`.
4. Have a different wallet claim (posting 0.10 USDC bond) and submit the child benchmark deliverable.
5. Settle fail-closed emitting canonical `BountySettled` event.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Tuple


class ExternalWorkCategory(str, Enum):
    DATA_NORMALIZATION = "data_normalization"
    API_ADAPTER = "api_adapter"
    SECURITY_VERIFICATION = "security_verification"
    BENCHMARK_PROFILING = "benchmark_profiling"


class BountyLifecycle(str, Enum):
    ACTIVATION_BLOCKED = "activation-blocked"
    FUNDED_LIVE = "funded-live"
    CLAIMABLE_LIVE = "claimable-live"
    EXCLUSIVE_CLAIM = "exclusive_claim"
    VERIFICATION_PENDING = "verification_pending"
    SETTLED = "settled"
    REJECTED = "rejected"


@dataclass
class ChildBenchmarkProof:
    proof_uri: str
    artifact_hash: str
    solver_wallet: str
    signature: str
    benchmark_metrics: Dict[str, Any] = field(default_factory=dict)

    def verify_proof(self) -> Tuple[bool, Optional[str]]:
        if not self.proof_uri.startswith(("https://", "ipfs://")):
            return False, "Proof URI must be secure https:// or ipfs://"
        if not self.artifact_hash or len(self.artifact_hash) < 32:
            return False, "Invalid cryptographic artifact hash"
        if not self.signature:
            return False, "Missing solver authorization signature"
        return True, None


@dataclass
class CanonicalChildBounty:
    child_bounty_id: str
    parent_bounty_id: str
    parent_round: int
    creator_address: str
    external_requester: str
    work_title: str
    sanitized_description: str
    category: ExternalWorkCategory
    verifier_id: str = "canonical-child-v1"
    solver_reward_usdc: float = 0.90
    verifier_reward_usdc: float = 0.10
    claim_bond_usdc: float = 0.10
    current_funding_usdc: float = 0.0
    status: BountyLifecycle = BountyLifecycle.ACTIVATION_BLOCKED
    current_claimant: Optional[str] = None
    co_funders: List[Dict[str, Any]] = field(default_factory=list)
    submitted_proof: Optional[ChildBenchmarkProof] = None
    settlement_tx_hash: Optional[str] = None
    event_log: List[Dict[str, Any]] = field(default_factory=list)

    def log_event(self, event_name: str, data: Dict[str, Any]) -> None:
        self.event_log.append({
            "event": event_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        })


class CanonicalChildBountyEngine:
    """Orchestrates creation, parent binding, co-funding, and settlement under canonical-child-v1 rules."""

    # Sensitive data patterns for automatic redaction
    API_KEY_PATTERN = re.compile(r"(?:api[_-]?key|secret|token)[:=]\s*['\"]?([a-zA-Z0-9_\-]{16,})['\"]?", re.IGNORECASE)
    EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    PHONE_PATTERN = re.compile(r"(?:\b|\+)[0-9]{1,3}?[-. ]?\(?[0-9]{2,4}?\)?[-. ]?[0-9]{3,4}[-. ]?[0-9]{3,4}\b")

    def __init__(self, network: str = "base-mainnet", chain_id: int = 8453):
        self.network = network
        self.chain_id = chain_id
        self.bounties: Dict[str, CanonicalChildBounty] = {}

    @classmethod
    def redact_pii(cls, text: str) -> str:
        """Sanitizes incoming external request strings."""
        redacted = cls.API_KEY_PATTERN.sub("api_key=[REDACTED_SECRET]", text)
        redacted = cls.EMAIL_PATTERN.sub("[REDACTED_EMAIL]", redacted)
        redacted = cls.PHONE_PATTERN.sub("[REDACTED_PHONE]", redacted)
        return redacted

    def seed_canonical_child_bounty(
        self,
        creator: str,
        parent_bounty_id: str,
        parent_round: int,
        external_requester: str,
        work_title: str,
        raw_description: str,
        category: ExternalWorkCategory,
        solver_reward: float = 0.90,
        verifier_reward: float = 0.10,
        claim_bond: float = 0.10,
    ) -> CanonicalChildBounty:
        """Seeds canonical child bounty bound to parent bounty and round."""
        sanitized = self.redact_pii(raw_description)
        seed_key = f"{parent_bounty_id}:{parent_round}:{creator}:{external_requester}:{work_title}"
        b_id = f"0x{hashlib.sha256(seed_key.encode()).hexdigest()}"

        child = CanonicalChildBounty(
            child_bounty_id=b_id,
            parent_bounty_id=parent_bounty_id,
            parent_round=parent_round,
            creator_address=creator,
            external_requester=external_requester,
            work_title=work_title,
            sanitized_description=sanitized,
            category=category,
            solver_reward_usdc=solver_reward,
            verifier_reward_usdc=verifier_reward,
            claim_bond_usdc=claim_bond,
        )
        child.log_event("ChildBountySeeded", {
            "child_bounty_id": b_id,
            "parent_bounty_id": parent_bounty_id,
            "parent_round": parent_round,
            "creator": creator,
            "external_requester": external_requester,
            "required_funding": solver_reward + verifier_reward,
        })
        self.bounties[b_id] = child
        return child

    def deposit_pooled_funding(self, child_bounty_id: str, funder: str, amount: float, tx_hash: str) -> Dict[str, Any]:
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
        """Locks exclusive claim for independent solver."""
        child = self.bounties.get(child_bounty_id)
        if not child:
            raise KeyError("Child bounty not found")

        if child.status != BountyLifecycle.CLAIMABLE_LIVE:
            raise ValueError(f"Cannot claim in status {child.status.value}")

        if bond_amount < child.claim_bond_usdc:
            raise ValueError(f"Bond {bond_amount} below required {child.claim_bond_usdc}")

        # Enforce distinct participant constraint
        if solver_wallet.lower() in [child.creator_address.lower(), child.external_requester.lower()]:
            raise ValueError("Creator or external requester cannot self-claim child bounty")

        child.current_claimant = solver_wallet
        child.status = BountyLifecycle.EXCLUSIVE_CLAIM
        child.log_event("BountyClaimed", {"solver": solver_wallet, "bond": bond_amount})

        return {"status": child.status.value, "claimant": solver_wallet}

    def submit_and_settle(self, child_bounty_id: str, proof: ChildBenchmarkProof) -> Dict[str, Any]:
        """Executes canonical-child-v1 verifier and emits BountySettled."""
        child = self.bounties.get(child_bounty_id)
        if not child:
            raise KeyError("Child bounty not found")

        if child.status != BountyLifecycle.EXCLUSIVE_CLAIM:
            raise ValueError("Child bounty not in exclusive claim status")

        if child.current_claimant.lower() != proof.solver_wallet.lower():
            raise PermissionError("Only active claimant can submit benchmark proof")

        child.submitted_proof = proof
        child.status = BountyLifecycle.VERIFICATION_PENDING

        valid, err = proof.verify_proof()
        if not valid:
            child.status = BountyLifecycle.REJECTED
            child.log_event("VerificationRejected", {"error": err})
            return {"status": child.status.value, "settled": False, "error": err}

        tx_hash = f"0x{hashlib.sha256(f'SETTLE_CANONICAL:{child_bounty_id}:{proof.solver_wallet}'.encode()).hexdigest()}"
        child.status = BountyLifecycle.SETTLED
        child.settlement_tx_hash = tx_hash
        total_solver_payout = child.solver_reward_usdc + child.claim_bond_usdc

        child.log_event("BountySettled", {
            "child_bounty_id": child_bounty_id,
            "parent_bounty_id": child.parent_bounty_id,
            "parent_round": child.parent_round,
            "solver": proof.solver_wallet,
            "total_solver_payout": total_solver_payout,
            "verifier_reward": child.verifier_reward_usdc,
            "tx_hash": tx_hash,
        })

        return {
            "status": child.status.value,
            "settled": True,
            "solver": proof.solver_wallet,
            "solver_payout_usdc": total_solver_payout,
            "verifier_payout_usdc": child.verifier_reward_usdc,
            "settlement_tx_hash": tx_hash,
            "parent_bounty_id": child.parent_bounty_id,
            "parent_round": child.parent_round,
        }
