"""
Arbitrary-precision settlement and reward calculation engine for Issue #1573.
"""

from decimal import Decimal, ROUND_HALF_UP
import re
from typing import Tuple
from packages.omni_boxy_guard.models import SettlementQuote


class BoxySettlementEngine:
    """Calculates financial escrow, coin rewards, and cryptocurrency payouts under REWARD_POLICY."""

    COIN_RATE = Decimal("1.25")
    REDEMPTION_RATE = Decimal("0.72")
    SATOSHIS_PER_BTC = 100_000_000
    PICONEROS_PER_XMR = 1_000_000_000_000
    LAMPORTS_PER_SOL = 1_000_000_000

    DEFAULT_EVM_ADDRESS = "0xdEF1aeE7055cE03c808d3feefb08B18bbC8596E9"
    DEFAULT_SOLANA_ADDRESS = "55D4Wx4ceLfgtQbNKnN97z5wEr55itibzEL83ANWqn1u"
    DEFAULT_STELLAR_ADDRESS = "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC"

    DEFAULT_BTC_PRICE = Decimal("65000.00")
    DEFAULT_XMR_PRICE = Decimal("150.00")
    DEFAULT_SOL_PRICE = Decimal("140.00")

    @classmethod
    def get_contributor_ratio(cls, usd_amount: Decimal) -> Decimal:
        """Determine contributor share ratio R based on bounty tier.

        Args:
            usd_amount: Total bounty value in USD.

        Returns:
            Decimal contributor split ratio R.
        """
        if usd_amount < Decimal("50"):
            return Decimal("0.95")
        if usd_amount <= Decimal("200"):
            return Decimal("0.92")
        if usd_amount <= Decimal("500"):
            return Decimal("0.90")
        if usd_amount <= Decimal("1000"):
            return Decimal("0.87")
        return Decimal("0.85")

    @classmethod
    def validate_evm_address(cls, address: str) -> bool:
        """Validate an EVM public key address format.

        Args:
            address: Ethereum/EVM hex address string.

        Returns:
            True if valid 42-character hex format, False otherwise.
        """
        if not address or not isinstance(address, str):
            return False
        return bool(re.match(r"^0x[a-fA-F0-9]{40}$", address.strip()))

    @classmethod
    def validate_stellar_address(cls, address: str) -> bool:
        """Validate a Stellar public StrKey address format.

        Args:
            address: Stellar account public key string.

        Returns:
            True if valid 56-character base32 format, False otherwise.
        """
        if not address or not isinstance(address, str):
            return False
        return bool(re.match(r"^[GC][A-Z2-7]{55}$", address.strip()))

    @classmethod
    def calculate_settlement(
        cls,
        usd_amount: Decimal,
        btc_price: Decimal = DEFAULT_BTC_PRICE,
        xmr_price: Decimal = DEFAULT_XMR_PRICE,
        sol_price: Decimal = DEFAULT_SOL_PRICE,
        evm_address: str = DEFAULT_EVM_ADDRESS,
        stellar_address: str = DEFAULT_STELLAR_ADDRESS,
        is_pppdud: bool = False,
    ) -> SettlementQuote:
        """Generate comprehensive settlement quote for an issue reward.

        Args:
            usd_amount: Bounty face value in USD.
            btc_price: BTC exchange rate in USD.
            xmr_price: XMR exchange rate in USD.
            sol_price: SOL exchange rate in USD.
            evm_address: EVM payout address.
            stellar_address: Stellar payout address.
            is_pppdud: Flag indicating if paid exclusively in PPPDUD joke currency.

        Returns:
            SettlementQuote with exact calculated conversions.
        """
        nominal_usd = usd_amount
        coins_total = (nominal_usd * cls.COIN_RATE).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        contributor_ratio = cls.get_contributor_ratio(nominal_usd)
        contributor_coins = (coins_total * contributor_ratio).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        net_cash_payout = (contributor_coins * cls.REDEMPTION_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        platform_fee = (nominal_usd - net_cash_payout).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        btc_amount = (net_cash_payout / btc_price).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
        satoshis = int(btc_amount * cls.SATOSHIS_PER_BTC)

        xmr_amount = (net_cash_payout / xmr_price).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
        sol_amount = (net_cash_payout / sol_price).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)

        ppp_dud_amount = nominal_usd
        ppp_dud_value = Decimal("0.00") if is_pppdud else net_cash_payout

        return SettlementQuote(
            nominal_usd=nominal_usd,
            real_usd=nominal_usd if not is_pppdud else Decimal("0.00"),
            coin_reward=coins_total,
            contributor_ratio=contributor_ratio,
            contributor_coins=contributor_coins,
            net_cash_payout_usd=net_cash_payout,
            platform_fee_usd=platform_fee,
            btc_amount=btc_amount,
            satoshis=satoshis,
            xmr_amount=xmr_amount,
            sol_amount=sol_amount,
            evm_address=evm_address,
            stellar_address=stellar_address,
            ppp_dud_amount=ppp_dud_amount,
            ppp_dud_value_usd=ppp_dud_value,
        )

    @classmethod
    def calculate_issue_1573_quotes(cls) -> Tuple[SettlementQuote, SettlementQuote, SettlementQuote]:
        """Calculate official settlement quotes for Issue #1573 base, real, and bonus reward tiers.

        Returns:
            Tuple of (base_100_quote, real_200_quote, total_300_quote).
        """
        base_quote = cls.calculate_settlement(Decimal("100.00"))
        real_quote = cls.calculate_settlement(Decimal("200.00"))
        bonus_quote = cls.calculate_settlement(Decimal("300.00"))
        return base_quote, real_quote, bonus_quote
