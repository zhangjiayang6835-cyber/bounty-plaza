"""Arbitrary-precision settlement engine for quadrillion-scale bounty payouts."""

from decimal import Decimal, ROUND_HALF_UP
import hashlib
import re
from typing import Optional
from .models import SettlementReceipt


class QuadrillionSettlementEngine:
    """Computes exact fractional accounting for Issue #1593 quadrillion bounty."""

    NOMINAL_BOUNTY_USD = Decimal("239398281948585883")
    ISSUE_REPORTED_COINS = Decimal("299247852435732352")
    COIN_RATE_PER_USD = Decimal("1.25")
    COIN_REDEMPTION_USD = Decimal("0.72")
    EXPIRY_WINDOW_SEC = 1800.0

    EVM_REGEX = re.compile(r"^0x[a-fA-F0-9]{40}$")
    STELLAR_REGEX = re.compile(r"^G[A-Z2-7]{55}$")

    CANONICAL_EVM = "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89"
    CANONICAL_STELLAR = "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC"

    @classmethod
    def get_contributor_ratio(cls, bounty_usd: Decimal) -> Decimal:
        """Determine contributor share ratio R based on REWARD_POLICY brackets."""
        if bounty_usd < Decimal("50"):
            return Decimal("0.95")
        if bounty_usd < Decimal("200"):
            return Decimal("0.92")
        if bounty_usd < Decimal("500"):
            return Decimal("0.90")
        if bounty_usd < Decimal("1000"):
            return Decimal("0.87")
        return Decimal("0.85")

    @classmethod
    def calculate_settlement(
        cls,
        nominal_usd: Optional[Decimal] = None,
        agreed_payout_usd: Optional[Decimal] = None,
        use_reported_coins: bool = False,
    ) -> dict[str, Decimal]:
        """Compute exact coin and cash distributions under the 'up to' clause."""
        base_usd = nominal_usd if nominal_usd is not None else cls.NOMINAL_BOUNTY_USD
        if base_usd < Decimal("0"):
            raise ValueError("Bounty amount cannot be negative")

        effective_usd = agreed_payout_usd if agreed_payout_usd is not None else base_usd
        if effective_usd < Decimal("0") or effective_usd > base_usd:
            raise ValueError("Agreed payout exceeds nominal bounty or is negative")

        if use_reported_coins and agreed_payout_usd is None:
            coins_total = cls.ISSUE_REPORTED_COINS
        else:
            coins_total = (effective_usd * cls.COIN_RATE_PER_USD).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            )

        ratio_r = cls.get_contributor_ratio(effective_usd)
        contributor_coins = (coins_total * ratio_r).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )

        contributor_cash = (contributor_coins * cls.COIN_REDEMPTION_USD).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        platform_fee = (effective_usd - contributor_cash).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return {
            "nominal_usd": base_usd,
            "effective_usd": effective_usd,
            "coins_total": coins_total,
            "contributor_ratio": ratio_r,
            "contributor_coins": contributor_coins,
            "contributor_cash_usd": contributor_cash,
            "platform_fee_usd": platform_fee,
        }

    @classmethod
    def validate_evm_address(cls, address: str) -> bool:
        """Validate 20-byte hexadecimal Ethereum address format."""
        if not address:
            return False
        return bool(cls.EVM_REGEX.match(address))

    @classmethod
    def validate_stellar_address(cls, address: str) -> bool:
        """Validate 56-character base32 encoded Stellar public key format."""
        if not address:
            return False
        return bool(cls.STELLAR_REGEX.match(address))

    @classmethod
    def verify_expiry(cls, issue_created_epoch: float, claim_epoch: float) -> bool:
        """Validate whether claim timestamp is within the 30-minute bounty expiry window."""
        elapsed = claim_epoch - issue_created_epoch
        return 0.0 <= elapsed <= cls.EXPIRY_WINDOW_SEC

    @classmethod
    def generate_receipt(
        cls,
        settlement_data: dict[str, Decimal],
        recipient_evm: str,
        recipient_stellar: str,
        timestamp_epoch: float,
    ) -> SettlementReceipt:
        """Construct immutable settlement receipt with deterministic SHA-256 digest."""
        if not cls.validate_evm_address(recipient_evm):
            raise ValueError("Invalid EVM recipient address")
        if not cls.validate_stellar_address(recipient_stellar):
            raise ValueError("Invalid Stellar recipient address")

        raw_payload = (
            f"{settlement_data['effective_usd']}:"
            f"{settlement_data['contributor_cash_usd']}:"
            f"{recipient_evm}:{recipient_stellar}:{timestamp_epoch:.3f}"
        )
        tx_hash = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

        return SettlementReceipt(
            nominal_bounty_usd=settlement_data["nominal_usd"],
            coins_total=settlement_data["coins_total"],
            contributor_ratio=settlement_data["contributor_ratio"],
            contributor_coins=settlement_data["contributor_coins"],
            contributor_cash_usd=settlement_data["contributor_cash_usd"],
            platform_fee_usd=settlement_data["platform_fee_usd"],
            recipient_evm=recipient_evm,
            recipient_stellar=recipient_stellar,
            timestamp_epoch=timestamp_epoch,
            tx_hash=tx_hash,
        )
