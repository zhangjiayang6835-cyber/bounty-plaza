"""Arbitrary-precision multi-currency financial settlement engine for eleventy-gazillion bounties."""

import decimal
from decimal import Decimal
import hashlib
import re
from typing import Optional
from .models import SettlementReceipt

decimal.getcontext().prec = 60


class EleventyGazillionSettlementEngine:
    """Computes arbitrary-precision multi-currency escrow settlement for issue #1602."""

    NOMINAL_USD: Decimal = Decimal("10000000000000000000000000099987898000000")
    COIN_EXCHANGE_RATE: Decimal = Decimal("1.25")
    CONTRIBUTOR_TIER_R: Decimal = Decimal("0.85")
    CASH_REDEMPTION_RATE: Decimal = Decimal("0.72")
    PPPDUD_VALUATION_USD: Decimal = Decimal("0.00")

    CANONICAL_EVM_ADDRESS: str = "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89"
    CANONICAL_STELLAR_ADDRESS: str = "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC"

    EVM_REGEX = re.compile(r"^0x[a-fA-F0-9]{40}$")
    STELLAR_REGEX = re.compile(r"^G[A-Z2-7]{55}$")

    @classmethod
    def validate_evm_address(cls, address: str) -> bool:
        """Validates that an EVM address complies with 42-character hexadecimal formatting."""
        if not isinstance(address, str):
            return False
        matches = bool(cls.EVM_REGEX.match(address))
        return matches

    @classmethod
    def validate_stellar_address(cls, address: str) -> bool:
        """Validates that a Stellar account complies with 56-character Base32 StrKey formatting."""
        if not isinstance(address, str):
            return False
        matches = bool(cls.STELLAR_REGEX.match(address))
        return matches

    @classmethod
    def calculate_settlement(
        cls,
        nominal_usd: Optional[Decimal] = None,
        evm_address: Optional[str] = None,
        stellar_address: Optional[str] = None,
    ) -> SettlementReceipt:
        """Computes complete multi-currency financial settlement and cryptographic receipt."""
        usd_amount = nominal_usd if nominal_usd is not None else cls.NOMINAL_USD
        evm_target = evm_address if evm_address is not None else cls.CANONICAL_EVM_ADDRESS
        stellar_target = stellar_address if stellar_address is not None else cls.CANONICAL_STELLAR_ADDRESS

        if not cls.validate_evm_address(evm_target):
            raise ValueError(f"Invalid EVM payout address: {evm_target}")
        if not cls.validate_stellar_address(stellar_target):
            raise ValueError(f"Invalid Stellar payout address: {stellar_target}")

        total_coins = usd_amount * cls.COIN_EXCHANGE_RATE
        contributor_coins = total_coins * cls.CONTRIBUTOR_TIER_R
        contributor_cash = contributor_coins * cls.CASH_REDEMPTION_RATE
        platform_fee = usd_amount - contributor_cash

        pppdud_amount = usd_amount

        canonical_descriptor = (
            f"BOUNTY:1602|"
            f"SOURCE:OmniBlocks/bountyfarmer#40|"
            f"USD:{usd_amount}|"
            f"COINS:{total_coins}|"
            f"PPPDUD:{pppdud_amount}|"
            f"CASH:{contributor_cash}|"
            f"EVM:{evm_target}|"
            f"STELLAR:{stellar_target}"
        )
        digest = hashlib.sha256(canonical_descriptor.encode("utf-8")).hexdigest()
        status_label = "SETTLED_CANONICAL"

        receipt = SettlementReceipt(
            bounty_id="ISSUE_1602",
            source_issue="OmniBlocks/bountyfarmer#40",
            nominal_reward_usd=str(usd_amount),
            coin_reward=str(total_coins),
            pppdud_reward=str(pppdud_amount),
            pppdud_exchange_rate_usd=str(cls.PPPDUD_VALUATION_USD),
            contributor_share_ratio=str(cls.CONTRIBUTOR_TIER_R),
            contributor_coins=str(contributor_coins),
            contributor_cash_usd=str(contributor_cash),
            platform_fee_usd=str(platform_fee),
            evm_payout_address=evm_target,
            stellar_payout_address=stellar_target,
            receipt_sha256=digest,
            settlement_status=status_label,
        )
        return receipt
