"""Financial reward settlement calculator adhering strictly to REWARD_POLICY.md."""

from packages.omni_forever_if.models import BountySettlement


class RewardSettlementCalculator:
    """Calculates coin conversion, contributor split, and cash redemption."""

    BASE_EXCHANGE_RATE: float = 1.25
    REDEMPTION_RATE: float = 0.72
    MINIMUM_REDEMPTION_COINS: float = 100.0

    @classmethod
    def get_contributor_ratio(cls, reward_usd: float) -> float:
        """Determine contributor revenue split ratio based on bounty bracket."""
        if reward_usd >= 1000.0:
            return 0.85
        if reward_usd >= 500.0:
            return 0.87
        if reward_usd >= 200.0:
            return 0.90
        if reward_usd >= 50.0:
            return 0.92
        return 0.95

    @classmethod
    def calculate_settlement(cls, reward_usd: float = 100.0) -> BountySettlement:
        """Compute platform coin allocation, contributor share, and net cash payout."""
        ratio = cls.get_contributor_ratio(reward_usd)
        total_coins = reward_usd * cls.BASE_EXCHANGE_RATE
        contributor_coins = total_coins * ratio
        net_cash = round(contributor_coins * cls.REDEMPTION_RATE, 2)
        platform_fee = round(reward_usd - net_cash, 2)
        omb_token_rate = 10.0
        omb_tokens = round(net_cash * omb_token_rate, 2)

        return BountySettlement(
            reward_usd=reward_usd,
            platform_coins=total_coins,
            contributor_ratio=ratio,
            contributor_coins=contributor_coins,
            redemption_rate_usd=cls.REDEMPTION_RATE,
            contributor_payout_usd=net_cash,
            platform_fee_usd=platform_fee,
            omb_tokens=omb_tokens,
        )

    @classmethod
    def is_eligible_for_redemption(cls, coins: float) -> bool:
        """Verify whether coin balance satisfies minimum redemption threshold."""
        return coins >= cls.MINIMUM_REDEMPTION_COINS


def compute_bounty_settlement(reward_usd: float = 100.0) -> BountySettlement:
    """Convenience function calculating bounty settlement for issue rewards."""
    return RewardSettlementCalculator.calculate_settlement(reward_usd)
