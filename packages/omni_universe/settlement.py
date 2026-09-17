"""
Arbitrary-precision financial settlement engine for Issue #1575 quadrillion-dollar escrow.
"""

from __future__ import annotations
import decimal
import hashlib
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SettlementReceipt:
    """Immutable audit record detailing multi-chain settlement and fee allocation."""

    receipt_id: str
    issue_id: int
    nominal_bounty_usd: str
    platform_coins_minted: str
    contributor_share_ratio: str
    contributor_coins_credited: str
    coin_to_cash_rate_usd: str
    net_contributor_payout_usd: str
    platform_treasury_fee_usd: str
    evm_payout_address: str
    stellar_payout_address: str
    settlement_hash: str


class QuadrillionSettlementEngine:
    """Exact decimal billing calculator compliant with REWARD_POLICY.md and BOUNTY_CONFIG.json."""

    ISSUE_ID: int = 1575
    STATED_BOUNTY_USD: str = "999999999999999999"
    STATED_COIN_REWARD: str = "1250000000000000000"
    BOUNTY_TO_COIN_RATE: str = "1.25"
    COIN_TO_CASH_RATE: str = "0.72"
    TREASURY_BSC_ADDRESS: str = "0x321984374e41e1c8ba3e2b87ab050828cffd25c2"

    EVM_REGEX = re.compile(r"^0x[0-9a-fA-F]{40}$")
    STELLAR_REGEX = re.compile(r"^G[A-Z2-7]{55}$")

    @classmethod
    def validate_evm_address(cls, address: str) -> bool:
        """Validate 20-byte hexadecimal Ethereum address format."""
        if not address or not isinstance(address, str):
            return False
        return bool(cls.EVM_REGEX.match(address))

    @classmethod
    def validate_stellar_address(cls, address: str) -> bool:
        """Validate 56-character Ed25519 public key StrKey format for Stellar network."""
        if not address or not isinstance(address, str):
            return False
        return bool(cls.STELLAR_REGEX.match(address))

    @classmethod
    def get_tier_ratio(cls, bounty_usd: decimal.Decimal) -> decimal.Decimal:
        """Return contributor share percentage R based on BOUNTY_CONFIG.json tier ladder."""
        if bounty_usd < decimal.Decimal("50"):
            return decimal.Decimal("0.95")
        if bounty_usd < decimal.Decimal("200"):
            return decimal.Decimal("0.92")
        if bounty_usd < decimal.Decimal("500"):
            return decimal.Decimal("0.90")
        if bounty_usd < decimal.Decimal("1000"):
            return decimal.Decimal("0.87")
        return decimal.Decimal("0.85")

    @classmethod
    def calculate_settlement(
        cls,
        evm_address: str,
        stellar_address: str,
        nominal_bounty_usd: str = STATED_BOUNTY_USD,
        coin_pool: str = STATED_COIN_REWARD,
    ) -> SettlementReceipt:
        """Execute exact arbitrary-precision settlement calculation without float truncation."""
        if not cls.validate_evm_address(evm_address):
            raise ValueError(f"Invalid EVM payout address: {evm_address}")
        if not cls.validate_stellar_address(stellar_address):
            raise ValueError(f"Invalid Stellar payout address: {stellar_address}")

        with decimal.localcontext() as ctx:
            ctx.prec = 50
            bounty_dec = decimal.Decimal(nominal_bounty_usd)
            coins_dec = decimal.Decimal(coin_pool)
            ratio = cls.get_tier_ratio(bounty_dec)
            rate_cash = decimal.Decimal(cls.COIN_TO_CASH_RATE)

            contributor_coins = coins_dec * ratio
            net_payout = contributor_coins * rate_cash
            treasury_fee = bounty_dec - net_payout

            payload = (
                f"{cls.ISSUE_ID}:{nominal_bounty_usd}:{coin_pool}:{ratio}:"
                f"{contributor_coins}:{net_payout}:{evm_address}:{stellar_address}"
            )
            settlement_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            receipt_id = f"receipt_1575_{settlement_hash[:16]}"

            return SettlementReceipt(
                receipt_id=receipt_id,
                issue_id=cls.ISSUE_ID,
                nominal_bounty_usd=str(bounty_dec),
                platform_coins_minted=str(coins_dec),
                contributor_share_ratio=str(ratio),
                contributor_coins_credited=str(contributor_coins),
                coin_to_cash_rate_usd=str(rate_cash),
                net_contributor_payout_usd=f"{net_payout:.2f}",
                platform_treasury_fee_usd=f"{treasury_fee:.2f}",
                evm_payout_address=evm_address,
                stellar_payout_address=stellar_address,
                settlement_hash=settlement_hash,
            )

    @classmethod
    def to_dict(cls, receipt: SettlementReceipt) -> dict[str, Any]:
        """Convert settlement receipt to serializable dictionary."""
        return {
            "receipt_id": receipt.receipt_id,
            "issue_id": receipt.issue_id,
            "nominal_bounty_usd": receipt.nominal_bounty_usd,
            "platform_coins_minted": receipt.platform_coins_minted,
            "contributor_share_ratio": receipt.contributor_share_ratio,
            "contributor_coins_credited": receipt.contributor_coins_credited,
            "coin_to_cash_rate_usd": receipt.coin_to_cash_rate_usd,
            "net_contributor_payout_usd": receipt.net_contributor_payout_usd,
            "platform_treasury_fee_usd": receipt.platform_treasury_fee_usd,
            "evm_payout_address": receipt.evm_payout_address,
            "stellar_payout_address": receipt.stellar_payout_address,
            "settlement_hash": receipt.settlement_hash,
        }
