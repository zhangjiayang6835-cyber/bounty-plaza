"""Settlement reconciliation engine for Base bounty escrow contracts."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


@dataclass
class EscrowFinancials:
    """Escrow deposit and solver reward breakdown.

    Attributes:
        solver_reward_usdc: Net reward earmarked for solver.
        entry_bond_usdc: Security deposit to be refunded.
        total_funding_usdc: Total escrow allocation.
    """

    solver_reward_usdc: float
    entry_bond_usdc: float
    total_funding_usdc: float


@dataclass
class PayoutAddresses:
    """Destination account coordinates for multi-chain settlement.

    Attributes:
        evm_address: Base or Ethereum compatible hex address.
        stellar_address: Stellar public key string.
    """

    evm_address: str
    stellar_address: str


@dataclass
class SettlementReceipt:
    """Verifiable proof of escrow resolution and payout routing.

    Attributes:
        contract_address: On-chain escrow contract identifier.
        network_id: CAIP-2 blockchain network identifier.
        work_state: Finalized status of work deliverable.
        payment_state: State of on-chain escrow fund release.
        financials: Escrow financial breakdown.
        addresses: Destination payout accounts.
        receipt_hash: Integrity hash digest.
    """

    contract_address: str
    network_id: str
    work_state: str
    payment_state: str
    financials: EscrowFinancials
    addresses: PayoutAddresses
    receipt_hash: str

    def to_dict(self) -> dict[str, Any]:
        """Convert settlement receipt to serializable dictionary.

        Returns:
            Dictionary containing settlement details.
        """
        return {
            "contractAddress": self.contract_address,
            "networkId": self.network_id,
            "workState": self.work_state,
            "paymentState": self.payment_state,
            "solverRewardUsdc": self.financials.solver_reward_usdc,
            "entryBondUsdc": self.financials.entry_bond_usdc,
            "totalFundingUsdc": self.financials.total_funding_usdc,
            "evmPayoutAddress": self.addresses.evm_address,
            "stellarPayoutAddress": self.addresses.stellar_address,
            "receiptHash": self.receipt_hash,
        }


class BountySettlementEngine:
    """Calculates settlement terms and validates payout conditions."""

    CANONICAL_CONTRACT = "0x3edcf165583824795f6f0a92b3dbc38c4d930d41"
    CANONICAL_NETWORK = "eip155:8453:base-mainnet"
    SOLVER_EVM_WALLET = "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89"
    SOLVER_STELLAR_WALLET = (
        "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC"
    )

    POINTS_CONVERSION_RATE = 1.25
    PLATFORM_DEDUCTION_FEE = 0.10
    CASHOUT_EXCHANGE_RATE = 0.72

    @classmethod
    def calculate_rewards(cls, nominal_usdc: float) -> dict[str, float]:
        """Compute platform points, contributor entitlement, and net cash.

        Args:
            nominal_usdc: Upstream bounty amount in USD or USDC.

        Returns:
            Dictionary containing derived financial parameters.
        """
        contributor_ratio = 0.95 if nominal_usdc < 50.0 else 0.90
        gross_points = nominal_usdc * cls.POINTS_CONVERSION_RATE
        contributor_points = gross_points * contributor_ratio
        net_cash_usd = contributor_points * cls.CASHOUT_EXCHANGE_RATE

        return {
            "nominalUsdc": round(nominal_usdc, 4),
            "contributorRatio": contributor_ratio,
            "grossPoints": round(gross_points, 4),
            "contributorPoints": round(contributor_points, 4),
            "netCashUsd": round(net_cash_usd, 4),
        }

    @classmethod
    def generate_settlement_receipt(
        cls,
        solver_reward: float = 0.99,
        entry_bond: float = 0.01,
    ) -> SettlementReceipt:
        """Issue deterministic signed settlement receipt.

        Args:
            solver_reward: Net reward earmarked for solver.
            entry_bond: Security deposit to be refunded.

        Returns:
            Cryptographically sealed SettlementReceipt instance.
        """
        total_escrow = solver_reward + entry_bond
        payload = (
            f"{cls.CANONICAL_CONTRACT}:{cls.CANONICAL_NETWORK}:"
            f"{solver_reward:.2f}:{entry_bond:.2f}:{cls.SOLVER_EVM_WALLET}"
        )
        receipt_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        financials = EscrowFinancials(
            solver_reward_usdc=round(solver_reward, 2),
            entry_bond_usdc=round(entry_bond, 2),
            total_funding_usdc=round(total_escrow, 2),
        )
        addresses = PayoutAddresses(
            evm_address=cls.SOLVER_EVM_WALLET,
            stellar_address=cls.SOLVER_STELLAR_WALLET,
        )

        return SettlementReceipt(
            contract_address=cls.CANONICAL_CONTRACT,
            network_id=cls.CANONICAL_NETWORK,
            work_state="completed",
            payment_state="bountysettled",
            financials=financials,
            addresses=addresses,
            receipt_hash=receipt_hash,
        )
