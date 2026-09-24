"""Settlement reconciliation and autonomous bounty escrow validation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Any

from packages.rpc_failover.models import SettlementTerms


DEFAULT_CONTRACT_ADDRESS = "0x26f0a0a60f8a1c12ca9b724062b9c5bfe8d013ce"
DEFAULT_BASE_CHAIN_ID = 8453
DEFAULT_SOLVER_PAYOUT_ADDRESS = "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89"


class SettlementReconciler:
    """Validator for autonomous bounty smart contract escrow settlement."""

    def __init__(self, terms: SettlementTerms | None = None) -> None:
        """Initialize settlement reconciler with specified terms.

        Args:
            terms: Canonical settlement parameters or default contract specification.
        """
        if terms is None:
            terms = SettlementTerms(
                network="base",
                contract_address=DEFAULT_CONTRACT_ADDRESS,
                solver_reward_usdc=0.99,
                claim_bond_usdc=0.01,
                total_funding_usdc=1.00,
                verifier_type="signed_quorum",
                quorum_threshold=1,
            )
        self.terms = terms

    def verify_financial_integrity(self) -> bool:
        """Verify that total escrow perfectly equals solver reward plus claim bond.

        Returns:
            True if micro-unit escrow sum matches total funding.
        """
        expected = (
            self.terms.solver_reward_base_units + self.terms.claim_bond_base_units
        )
        return expected == self.terms.total_funding_base_units

    def generate_settlement_digest(
        self,
        bounty_id: str,
        claimant_address: str = DEFAULT_SOLVER_PAYOUT_ADDRESS,
    ) -> str:
        """Compute deterministic SHA-256 digest commitment for settlement claims.

        Args:
            bounty_id: Identifier of the target bounty task.
            claimant_address: Receiving wallet address for settlement funds.

        Returns:
            Hex-encoded hash digest commitment.
        """
        payload = {
            "bounty_id": bounty_id,
            "claimant": claimant_address.lower(),
            "contract": self.terms.contract_address.lower(),
            "network": self.terms.network,
            "solver_reward_base_units": self.terms.solver_reward_base_units,
            "claim_bond_base_units": self.terms.claim_bond_base_units,
            "total_funding_base_units": self.terms.total_funding_base_units,
            "verifier_type": self.terms.verifier_type,
            "quorum_threshold": self.terms.quorum_threshold,
        }
        serialized = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    def serialize_summary(self) -> dict[str, Any]:
        """Produce dictionary summary of terms and micro-unit amounts.

        Returns:
            Dictionary containing formatted terms and unit values.
        """
        data = asdict(self.terms)
        data["solver_reward_base_units"] = self.terms.solver_reward_base_units
        data["claim_bond_base_units"] = self.terms.claim_bond_base_units
        data["total_funding_base_units"] = self.terms.total_funding_base_units
        data["is_balanced"] = self.verify_financial_integrity()
        return data
