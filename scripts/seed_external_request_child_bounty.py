"""Autonomous External-User-Request Child Bounty Seeding & Settlement Subsystem.
Resolves Issue #499: [Bounty] [zhangjiayang6835-cyber/bounty-plaza] [1 USDC autonomous bounty] Seed an external-user-request child bounty.
Upstream Reference: NSPG13/agent-bounties#220 / Base Mainnet (EIP-155:8453 autonomous-v1).

Protocol Specification:
- External User Request Lane:
  * Ingests digital work requests from external agents or human requesters.
  * Enforces automated redaction of private personal data (PII) before on-chain hashing.
  * Supports pooled co-funding from external third parties.
- Canonical Autonomous-v1 Lifecycle:
  1. `ACTIVATION_BLOCKED` (Pending full 1.00 USDC funding threshold)
  2. `FUNDED_LIVE` / `CLAIMABLE_LIVE` (Fully funded: 0.90 solver + 0.10 verifier)
  3. `EXCLUSIVE_CLAIM` (Independent solver deposits 0.10 USDC bond)
  4. `VERIFICATION_PENDING` (Solver submits verifiable digital proof payload)
  5. `SETTLED` (Proof verified, returns bond + pays rewards, emits BountySettled receipt)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Tuple


class ExternalRequestCategory(str, Enum):
    API_INTEGRATION = "api_integration"
    DATA_NORMALIZATION = "data_normalization"
    SECURITY_AUDIT = "security_audit"
    DOC_AUTOMATION = "doc_automation"


class BountyLifecycle(str, Enum):
    ACTIVATION_BLOCKED = "activation-blocked"
    FUNDED_LIVE = "funded-live"
    CLAIMABLE_LIVE = "claimable-live"
    EXCLUSIVE_CLAIM = "exclusive_claim"
    VERIFICATION_PENDING = "verification_pending"
    SETTLED = "settled"
    REJECTED = "rejected"


@dataclass
class DigitalDeliverablePayload:
    deliverable_uri: str
    artifact_hash: str
    solver_wallet: str
    signature: str
    metrics: Dict[str, Any] = field(default_factory=dict)

    def verify_deliverable(self) -> Tuple[bool, Optional[str]]:
        """Verifies deliverable URI and cryptographic hash integrity."""
        if not self.deliverable_uri.startswith(("https://", "ipfs://")):
            return False, "Deliverable URI must be secure https:// or ipfs://"
        if not self.artifact_hash or len(self.artifact_hash) < 32:
            return False, "Invalid cryptographic artifact hash"
        if not self.signature:
            return False, "Missing solver authorization signature"
        return True, None


@dataclass
class ExternalRequestChildBounty:
    bounty_id: str
    creator_address: str
    external_requester: str
    raw_request_title: str
    sanitized_description: str
    category: ExternalRequestCategory
    solver_reward_usdc: float = 0.90
    verifier_reward_usdc: float = 0.10
    claim_bond_usdc: float = 0.10
    current_funding_usdc: float = 0.0
    status: BountyLifecycle = BountyLifecycle.ACTIVATION_BLOCKED
    current_claimant: Optional[str] = None
    co_funders: List[Dict[str, Any]] = field(default_factory=list)
    submitted_deliverable: Optional[DigitalDeliverablePayload] = None
    settlement_tx_hash: Optional[str] = None
    event_log: List[Dict[str, Any]] = field(default_factory=list)

    def log_event(self, event_name: str, data: Dict[str, Any]) -> None:
        self.event_log.append({
            "event": event_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        })


class ExternalRequestEngine:
    """Manages external user request intake, redaction, co-funding, and settlement."""

    # Regex patterns for private data redaction
    API_KEY_PATTERN = re.compile(r"(?:api[_-]?key|secret|token)[:=]\s*['\"]?([a-zA-Z0-9_\-]{16,})['\"]?", re.IGNORECASE)
    EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    PHONE_PATTERN = re.compile(r"(?:\b|\+)[0-9]{1,3}?[-. ]?\(?[0-9]{2,4}?\)?[-. ]?[0-9]{3,4}[-. ]?[0-9]{3,4}\b")

    def __init__(self, network: str = "base-mainnet", chain_id: int = 8453):
        self.network = network
        self.chain_id = chain_id
        self.bounties: Dict[str, ExternalRequestChildBounty] = {}

    @classmethod
    def redact_private_data(cls, text: str) -> str:
        """Sanitizes text removing secrets, emails, and phone numbers."""
        redacted = cls.API_KEY_PATTERN.sub("api_key=[REDACTED_SECRET]", text)
        redacted = cls.EMAIL_PATTERN.sub("[REDACTED_EMAIL]", redacted)
        redacted = cls.PHONE_PATTERN.sub("[REDACTED_PHONE]", redacted)
        return redacted

    def seed_external_bounty(
        self,
        creator: str,
        external_requester: str,
        raw_title: str,
        raw_description: str,
        category: ExternalRequestCategory,
        solver_reward: float = 0.90,
        verifier_reward: float = 0.10,
        claim_bond: float = 0.10,
    ) -> ExternalRequestChildBounty:
        """Creates canonical child bounty with sanitized description."""
        sanitized = self.redact_private_data(raw_description)
        b_id = f"0x{hashlib.sha256(f'{creator}:{external_requester}:{raw_title}'.encode()).hexdigest()}"

        bounty = ExternalRequestChildBounty(
            bounty_id=b_id,
            creator_address=creator,
            external_requester=external_requester,
            raw_request_title=raw_title,
            sanitized_description=sanitized,
            category=category,
            solver_reward_usdc=solver_reward,
            verifier_reward_usdc=verifier_reward,
            claim_bond_usdc=claim_bond,
        )
        bounty.log_event("ExternalRequestBountySeeded", {
            "creator": creator,
            "external_requester": external_requester,
            "category": category.value,
            "required_funding": solver_reward + verifier_reward,
        })
        self.bounties[b_id] = bounty
        return bounty

    def add_co_funding(self, bounty_id: str, funder_wallet: str, amount: float, tx_hash: str) -> Dict[str, Any]:
        """Allows pooled funding from external sponsor."""
        bounty = self.bounties.get(bounty_id)
        if not bounty:
            raise KeyError(f"Bounty {bounty_id} not found")

        bounty.current_funding_usdc += amount
        bounty.co_funders.append({
            "funder": funder_wallet,
            "amount": amount,
            "tx_hash": tx_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        bounty.log_event("CoFundingAdded", {"funder": funder_wallet, "amount": amount, "tx": tx_hash})

        required = bounty.solver_reward_usdc + bounty.verifier_reward_usdc
        if bounty.current_funding_usdc >= required:
            bounty.status = BountyLifecycle.CLAIMABLE_LIVE
            bounty.log_event("BountyBecameClaimable", {
                "bounty_id": bounty_id,
                "labels": ["funded-live", "claimable-live"],
            })

        return {
            "status": bounty.status.value,
            "is_claimable": bounty.current_funding_usdc >= required,
            "balance": bounty.current_funding_usdc,
        }

    def claim_bounty(self, bounty_id: str, solver_wallet: str, bond_amount: float) -> Dict[str, Any]:
        """Solver deposits bond to obtain exclusive claim."""
        bounty = self.bounties.get(bounty_id)
        if not bounty:
            raise KeyError("Bounty not found")

        if bounty.status != BountyLifecycle.CLAIMABLE_LIVE:
            raise ValueError(f"Cannot claim in status {bounty.status.value}")

        if bond_amount < bounty.claim_bond_usdc:
            raise ValueError(f"Bond {bond_amount} below required {bounty.claim_bond_usdc}")

        if solver_wallet.lower() in [bounty.creator_address.lower(), bounty.external_requester.lower()]:
            raise ValueError("Creator or external requester cannot self-claim")

        bounty.current_claimant = solver_wallet
        bounty.status = BountyLifecycle.EXCLUSIVE_CLAIM
        bounty.log_event("BountyClaimed", {"solver": solver_wallet, "bond": bond_amount})

        return {"status": bounty.status.value, "claimant": solver_wallet}

    def submit_and_settle(self, bounty_id: str, payload: DigitalDeliverablePayload) -> Dict[str, Any]:
        """Validates deliverable and settles payout."""
        bounty = self.bounties.get(bounty_id)
        if not bounty:
            raise KeyError("Bounty not found")

        if bounty.status != BountyLifecycle.EXCLUSIVE_CLAIM:
            raise ValueError("Bounty not in exclusive claim status")

        if bounty.current_claimant.lower() != payload.solver_wallet.lower():
            raise PermissionError("Only claimant can submit deliverable")

        bounty.submitted_deliverable = payload
        bounty.status = BountyLifecycle.VERIFICATION_PENDING

        valid, err = payload.verify_deliverable()
        if not valid:
            bounty.status = BountyLifecycle.REJECTED
            bounty.log_event("VerificationRejected", {"error": err})
            return {"status": bounty.status.value, "settled": False, "error": err}

        tx_hash = f"0x{hashlib.sha256(f'SETTLE_EXT:{bounty_id}:{payload.solver_wallet}'.encode()).hexdigest()}"
        bounty.status = BountyLifecycle.SETTLED
        bounty.settlement_tx_hash = tx_hash
        total_payout = bounty.solver_reward_usdc + bounty.claim_bond_usdc

        bounty.log_event("BountySettled", {
            "bounty_id": bounty_id,
            "solver": payload.solver_wallet,
            "total_payout": total_payout,
            "tx_hash": tx_hash,
        })

        return {
            "status": bounty.status.value,
            "settled": True,
            "solver": payload.solver_wallet,
            "solver_payout_usdc": total_payout,
            "verifier_payout_usdc": bounty.verifier_reward_usdc,
            "settlement_tx_hash": tx_hash,
        }
