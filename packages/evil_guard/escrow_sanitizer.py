"""Escrow and numerical currency bounds sanitization engine."""

from decimal import Decimal, InvalidOperation
from typing import Union

from packages.evil_guard.models import BountyPayoutBreakdown, SanitizedBounty

DEFAULT_MAX_BOUNTY_USD = Decimal("10000000")
COIN_MULTIPLIER = Decimal("1.25")
EXCHANGE_RATE = Decimal("0.72")
SQLITE_MAX_INT = Decimal("9223372036854775807")


class EscrowSanitizer:
    """Safeguards financial computations against astronomical numbers and overflows."""

    def __init__(self, max_bounty_usd: Decimal = DEFAULT_MAX_BOUNTY_USD):
        """Initialize sanitizer with upper boundary threshold."""
        self.max_bounty_usd = max_bounty_usd

    def get_contributor_ratio(self, amount_usd: Decimal) -> Decimal:
        """Derive contributor cut ratio based on the official tiered reward policy."""
        if amount_usd < Decimal("50"):
            return Decimal("0.95")
        if amount_usd < Decimal("200"):
            return Decimal("0.92")
        if amount_usd < Decimal("500"):
            return Decimal("0.90")
        if amount_usd < Decimal("1000"):
            return Decimal("0.87")
        return Decimal("0.85")

    def _parse_amount(self, raw_amount: Union[int, float, str, Decimal]) -> Decimal:
        """Clean string representation and parse into Decimal safely."""
        try:
            cleaned = str(raw_amount).replace(",", "").replace("$", "").strip()
            parsed = Decimal(cleaned)
        except (InvalidOperation, TypeError, ValueError):
            parsed = Decimal("0")
        return max(parsed, Decimal("0"))

    def _calculate_payout(
        self, effective_amount: Decimal, coin_reward: int
    ) -> BountyPayoutBreakdown:
        """Compute contributor ratio, coins, and fiat cash payout."""
        ratio = self.get_contributor_ratio(effective_amount)
        contributor_coins_dec = Decimal(coin_reward) * ratio
        contributor_coins = int(contributor_coins_dec.quantize(Decimal("1")))
        cash_payout = (Decimal(contributor_coins) * EXCHANGE_RATE).quantize(Decimal("0.01"))
        return BountyPayoutBreakdown(
            contributor_ratio=ratio,
            contributor_coins=contributor_coins,
            cash_payout_usd=cash_payout,
        )

    def sanitize(
        self,
        raw_amount: Union[int, float, str, Decimal],
        clamp_astronomical: bool = True,
    ) -> SanitizedBounty:
        """Parse raw amount, prevent arithmetic overflow, and compute exact payouts."""
        amount_decimal = self._parse_amount(raw_amount)

        is_astronomical = (
            amount_decimal > self.max_bounty_usd
            or (amount_decimal * COIN_MULTIPLIER) > SQLITE_MAX_INT
        )

        is_clamped = False
        if is_astronomical and clamp_astronomical:
            effective_amount = self.max_bounty_usd
            is_clamped = True
            status_note = (
                f"Astronomical amount {amount_decimal} clamped to ceiling {self.max_bounty_usd} USD"
            )
        else:
            effective_amount = amount_decimal
            status_note = "Amount within acceptable numerical boundaries"

        coin_reward_dec = effective_amount * COIN_MULTIPLIER
        coin_reward = int(coin_reward_dec.quantize(Decimal("1")))

        payout = self._calculate_payout(effective_amount, coin_reward)

        return SanitizedBounty(
            original_amount_usd=amount_decimal,
            sanitized_amount_usd=effective_amount,
            coin_reward=coin_reward,
            payout=payout,
            is_astronomical=is_astronomical,
            is_clamped=is_clamped,
            status_note=status_note,
        )
