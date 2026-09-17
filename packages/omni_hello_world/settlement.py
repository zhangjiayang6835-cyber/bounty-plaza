"""
Settlement calculation engine for Bounty Plaza Issue #1560 under REWARD_POLICY.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Tuple

USD_TO_COIN_RATE = Decimal("1.25")
COIN_TO_USD_RATE = Decimal("0.72")
PLATFORM_FEE_RATE = Decimal("0.10")

EVM_PAYOUT_ADDRESS = "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89"
STELLAR_PAYOUT_ADDRESS = "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC"


@dataclass(frozen=True)
class BountySettlement:
    """Financial settlement breakdown according to REWARD_POLICY specifications."""

    nominal_usd: Decimal
    total_coins: Decimal
    contributor_ratio: Decimal
    contributor_coins: Decimal
    cash_payout_usd: Decimal
    platform_cut_usd: Decimal
    evm_address: str
    stellar_address: str


def determine_contributor_ratio(nominal_usd: Decimal) -> Decimal:
    """Determine the contributor split ratio R based on bounty brackets."""
    if nominal_usd < Decimal("50.00"):
        return Decimal("0.95")
    if nominal_usd <= Decimal("200.00"):
        return Decimal("0.92")
    if nominal_usd <= Decimal("500.00"):
        return Decimal("0.90")
    if nominal_usd <= Decimal("1000.00"):
        return Decimal("0.87")
    return Decimal("0.85")


def calculate_settlement(
    nominal_usd: Decimal = Decimal("100.00"),
    evm_address: str = EVM_PAYOUT_ADDRESS,
    stellar_address: str = STELLAR_PAYOUT_ADDRESS,
) -> BountySettlement:
    """Calculate the exact coin and fiat breakdown for a bounty issue."""
    ratio = determine_contributor_ratio(nominal_usd)
    total_coins = (nominal_usd * USD_TO_COIN_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    contributor_coins = (total_coins * ratio).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    cash_payout = (contributor_coins * COIN_TO_USD_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    platform_cut = (nominal_usd - cash_payout).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return BountySettlement(
        nominal_usd=nominal_usd,
        total_coins=total_coins,
        contributor_ratio=ratio,
        contributor_coins=contributor_coins,
        cash_payout_usd=cash_payout,
        platform_cut_usd=platform_cut,
        evm_address=evm_address,
        stellar_address=stellar_address,
    )


def format_settlement_summary(settlement: BountySettlement) -> Tuple[str, str, str, str]:
    """Return key financial figures formatted for reporting."""
    nominal_str = f"${settlement.nominal_usd:.2f}"
    coins_str = f"{settlement.total_coins} coins"
    contributor_coins_str = f"{settlement.contributor_coins} coins"
    cash_str = f"${settlement.cash_payout_usd:.2f}"
    return (nominal_str, coins_str, contributor_coins_str, cash_str)
