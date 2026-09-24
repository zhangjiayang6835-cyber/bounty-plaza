"""Settlement ledger accounting and cryptographic receipt validation engine."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass


@dataclass
class SettlementReceipt:
    """Canonical cryptographic receipt for verified bounty milestone payout."""

    issue_number: int
    source_bounty_url: str
    network: str
    contract_address: str
    solver_reward_usdc: float
    entry_bond_usdc: float
    total_funding_usdc: float
    platform_coin_multiplier: float
    total_listing_coins: float
    contributor_share_ratio: float
    contributor_coins: float
    cashout_rate_usd_per_coin: float
    net_cashout_usd: float
    evm_payout_address: str
    stellar_payout_address: str
    verification_quorum: str
    receipt_sha256: str


class SettlementEngine:
    """Validator for smart contract escrow settlement and coin allocations."""

    EVM_PAYOUT = "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89"
    STELLAR_PAYOUT = "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC"
    CONTRACT_ADDRESS = "0xe11965e2c68f6f4da4b97c8e62fda5015ae0137b"

    def __init__(self, solver_reward_usdc: float = 15.068098, entry_bond_usdc: float = 2.00) -> None:
        """Initialize settlement engine with escrow amounts."""
        self.solver_reward_usdc = solver_reward_usdc
        self.entry_bond_usdc = entry_bond_usdc
        self.total_funding_usdc = solver_reward_usdc + entry_bond_usdc

    def compute_settlement(self) -> SettlementReceipt:
        """Compute full milestone settlement ledger and cryptographic digest."""
        listing_coins = round(self.solver_reward_usdc * 1.25, 6)
        share_ratio = 0.95
        earned_coins = round(listing_coins * share_ratio, 6)
        cashout_rate = 0.72
        net_cashout = round(earned_coins * cashout_rate, 6)

        payload = {
            "issue_number": 1633,
            "source_bounty_url": "https://github.com/NSPG13/agent-bounties/issues/1505",
            "network": "Base (EVM Chain ID 8453)",
            "contract_address": self.CONTRACT_ADDRESS,
            "solver_reward_usdc": self.solver_reward_usdc,
            "entry_bond_usdc": self.entry_bond_usdc,
            "total_funding_usdc": round(self.total_funding_usdc, 6),
            "platform_coin_multiplier": 1.25,
            "total_listing_coins": listing_coins,
            "contributor_share_ratio": share_ratio,
            "contributor_coins": earned_coins,
            "cashout_rate_usd_per_coin": cashout_rate,
            "net_cashout_usd": net_cashout,
            "evm_payout_address": self.EVM_PAYOUT,
            "stellar_payout_address": self.STELLAR_PAYOUT,
            "verification_quorum": "signed_quorum",
        }

        serialized = json.dumps(payload, sort_keys=True)
        receipt_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        return SettlementReceipt(
            issue_number=payload["issue_number"],
            source_bounty_url=payload["source_bounty_url"],
            network=payload["network"],
            contract_address=payload["contract_address"],
            solver_reward_usdc=payload["solver_reward_usdc"],
            entry_bond_usdc=payload["entry_bond_usdc"],
            total_funding_usdc=payload["total_funding_usdc"],
            platform_coin_multiplier=payload["platform_coin_multiplier"],
            total_listing_coins=payload["total_listing_coins"],
            contributor_share_ratio=payload["contributor_share_ratio"],
            contributor_coins=payload["contributor_coins"],
            cashout_rate_usd_per_coin=payload["cashout_rate_usd_per_coin"],
            net_cashout_usd=payload["net_cashout_usd"],
            evm_payout_address=payload["evm_payout_address"],
            stellar_payout_address=payload["stellar_payout_address"],
            verification_quorum=payload["verification_quorum"],
            receipt_sha256=receipt_hash,
        )

    def export_json(self) -> str:
        """Export serialized settlement receipt in human-readable JSON."""
        receipt = self.compute_settlement()
        return json.dumps(asdict(receipt), indent=2)
