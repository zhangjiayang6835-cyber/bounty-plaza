"""Financial settlement and reward policy verification engine for Issue #1584."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import re

EVM_PAYOUT_ADDRESS = "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89"
STELLAR_PAYOUT_ADDRESS = "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC"

COIN_RATE = Decimal("1.25")
REDEMPTION_RATE = Decimal("0.72")
PLATFORM_FEE_RATE = Decimal("0.10")
NOMINAL_BOUNTY_1584 = Decimal("1500.00")


@dataclass(frozen=True)
class BountySettlement:
    """Immutable data record encapsulating financial breakdown for a bounty task."""

    nominal_usd: Decimal
    total_coins: Decimal
    contributor_ratio: Decimal
    contributor_coins: Decimal
    cash_payout_usd: Decimal
    platform_fee_usd: Decimal
    effective_payout_percentage: Decimal
    evm_address: str
    stellar_address: str


def get_contributor_ratio(bounty_usd: Decimal) -> Decimal:
    """Return contributor reward split ratio based on bounty tier brackets."""
    if bounty_usd < Decimal("50.00"):
        ratio = Decimal("0.95")
    elif bounty_usd < Decimal("200.00"):
        ratio = Decimal("0.92")
    elif bounty_usd < Decimal("500.00"):
        ratio = Decimal("0.90")
    elif bounty_usd < Decimal("1000.00"):
        ratio = Decimal("0.87")
    else:
        ratio = Decimal("0.85")
    return ratio


def calculate_settlement(
    nominal_usd: Decimal = NOMINAL_BOUNTY_1584,
    evm_address: str = EVM_PAYOUT_ADDRESS,
    stellar_address: str = STELLAR_PAYOUT_ADDRESS,
) -> BountySettlement:
    """Compute exact financial reward numbers under REWARD_POLICY specifications."""
    total_coins = (nominal_usd * COIN_RATE).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )
    ratio = get_contributor_ratio(nominal_usd)
    contributor_coins = (total_coins * ratio).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )
    cash_payout = (contributor_coins * REDEMPTION_RATE).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    platform_fee = (nominal_usd - cash_payout).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    effective_pct = (cash_payout / nominal_usd * Decimal("100.00")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    settlement = BountySettlement(
        nominal_usd=nominal_usd,
        total_coins=total_coins,
        contributor_ratio=ratio,
        contributor_coins=contributor_coins,
        cash_payout_usd=cash_payout,
        platform_fee_usd=platform_fee,
        effective_payout_percentage=effective_pct,
        evm_address=evm_address,
        stellar_address=stellar_address,
    )
    return settlement


def validate_evm_address(address: str) -> bool:
    """Validate checksummed or lowercase EVM hexadecimal address format."""
    pattern = r"^0x[a-fA-F0-9]{40}$"
    is_valid = bool(re.match(pattern, address))
    return is_valid


def validate_stellar_address(address: str) -> bool:
    """Validate public StrKey encoded Stellar account address format."""
    pattern = r"^G[A-Z2-7]{55}$"
    is_valid = bool(re.match(pattern, address))
    return is_valid
