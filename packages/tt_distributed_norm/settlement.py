"""Arbitrary-precision bounty settlement calculations and receipt generation."""

from decimal import Decimal, ROUND_HALF_UP
import hashlib
import re
from typing import Dict

EVM_ADDRESS_PATTERN = r"^0x[a-fA-F0-9]{40}$"
STELLAR_ADDRESS_PATTERN = r"^G[A-Z2-7]{55}$"


def validate_evm_address(address: str) -> bool:
    """Validate that the given string matches standard EVM hex address format."""
    if not isinstance(address, str):
        return False
    return bool(re.match(EVM_ADDRESS_PATTERN, address))


def validate_stellar_address(address: str) -> bool:
    """Validate that the given string matches standard Stellar public key format."""
    if not isinstance(address, str):
        return False
    return bool(re.match(STELLAR_ADDRESS_PATTERN, address))


def get_contributor_tier_ratio(usd_amount: Decimal) -> Decimal:
    """Determine contributor payout ratio based on tiered bracket policy."""
    if usd_amount <= Decimal("50.00"):
        return Decimal("0.50")
    if usd_amount <= Decimal("200.00"):
        return Decimal("0.60")
    if usd_amount <= Decimal("500.00"):
        return Decimal("0.70")
    if usd_amount <= Decimal("1000.00"):
        return Decimal("0.75")
    return Decimal("0.85")


class BountySettlementEngine:
    """Calculates exact financial breakdown and produces cryptographic receipts."""

    def __init__(
        self,
        nominal_usd: str = "3000.00",
        coin_conversion_rate: str = "1.25",
        coin_redemption_rate: str = "0.72",
    ):
        """Initialize settlement engine with nominal currency rates."""
        self.nominal_usd = Decimal(nominal_usd)
        self.coin_conversion_rate = Decimal(coin_conversion_rate)
        self.coin_redemption_rate = Decimal(coin_redemption_rate)

    def compute_settlement(
        self,
        evm_recipient: str,
        stellar_recipient: str,
        issue_id: int = 1589,
    ) -> Dict[str, object]:
        """Compute full accounting breakdown and generate settlement receipt."""
        is_evm_valid = validate_evm_address(evm_recipient)
        is_stellar_valid = validate_stellar_address(stellar_recipient)

        if not is_evm_valid or not is_stellar_valid:
            status_desc = "invalid_addresses"
            return {
                "status": status_desc,
                "is_valid": False,
                "nominal_usd": str(self.nominal_usd),
            }

        coins_total = (self.nominal_usd * self.coin_conversion_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        ratio = get_contributor_tier_ratio(self.nominal_usd)
        contributor_coins = (coins_total * ratio).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        platform_coins = coins_total - contributor_coins

        contributor_cash_usd = (contributor_coins * self.coin_redemption_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        platform_fee_usd = self.nominal_usd - contributor_cash_usd

        receipt_raw = f"{issue_id}:{self.nominal_usd}:{coins_total}:{evm_recipient}:{stellar_recipient}"
        tx_hash = hashlib.sha256(receipt_raw.encode("utf-8")).hexdigest()

        return {
            "status": "cleared",
            "is_valid": True,
            "issue_id": issue_id,
            "nominal_usd": str(self.nominal_usd),
            "coins_total": str(coins_total),
            "contributor_ratio": str(ratio),
            "contributor_coins": str(contributor_coins),
            "platform_coins": str(platform_coins),
            "contributor_cash_usd": str(contributor_cash_usd),
            "platform_fee_usd": str(platform_fee_usd),
            "evm_recipient": evm_recipient,
            "stellar_recipient": stellar_recipient,
            "tx_hash": tx_hash,
        }
