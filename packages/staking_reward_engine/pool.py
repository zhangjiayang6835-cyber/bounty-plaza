"""Staking reward accrual state machine with Q64.64 fixed-point arithmetic."""

from dataclasses import dataclass

MAX_U64: int = (1 << 64) - 1
MAX_U128: int = (1 << 128) - 1
Q64_SCALE: int = 1 << 64
Q64_FRACTIONAL_MASK: int = (1 << 64) - 1


class PoolError(Exception):
    """Base exception for all staking pool calculation errors."""


class RewardCalcOverflow(PoolError):
    """Raised when an intermediate or final reward calculation overflows bounds."""


class RewardCalcDivByZero(PoolError):
    """Raised when a division operation attempts to divide by zero."""


class RewardCalcUnderflow(PoolError):
    """Raised when a subtraction or shift results in an underflow."""


class RewardOverflow(PoolError):
    """Raised when fixed point multiplication overflows."""


class RewardUnderflow(PoolError):
    """Raised when fixed point division underflows."""


def checked_mul(a: int, b: int) -> int:
    """Multiplies two unsigned 128-bit integers with overflow protection.

    Args:
        a: First integer operand.
        b: Second integer operand.

    Returns:
        Product of a and b.

    Raises:
        RewardCalcOverflow: If the product exceeds MAX_U128.
    """
    res = a * b
    if res > MAX_U128 or res < 0:
        raise RewardCalcOverflow("Multiplication overflowed 128-bit boundary")
    return res


def checked_div(numerator: int, denominator: int) -> int:
    """Divides two unsigned 128-bit integers with zero division protection.

    Args:
        numerator: Numerator operand.
        denominator: Denominator operand.

    Returns:
        Quotient of integer division.

    Raises:
        RewardCalcDivByZero: If denominator is zero.
        RewardCalcOverflow: If numerator or denominator are negative.
    """
    if denominator == 0:
        raise RewardCalcDivByZero("Division by zero in pool reward calculation")
    if numerator < 0 or denominator < 0:
        raise RewardCalcOverflow("Negative integer supplied to unsigned division")
    return numerator // denominator


def accrue_rewards(
    accumulated_rewards_per_share: int,
    total_staked_tokens: int,
    pending_rewards: int,
) -> int:
    """Accrues pending rewards to the accumulator using Q64.64 fixed-point arithmetic.

    Args:
        accumulated_rewards_per_share: Current Q64.64 reward accumulator.
        total_staked_tokens: Total tokens currently staked in the pool.
        pending_rewards: Newly accrued reward tokens to distribute.

    Returns:
        Updated accumulated_rewards_per_share as a Q64.64 integer.

    Raises:
        RewardCalcDivByZero: If total_staked_tokens is zero.
        RewardCalcOverflow: If intermediate or final addition exceeds MAX_U128.
    """
    if total_staked_tokens == 0:
        raise RewardCalcDivByZero("Cannot accrue rewards when total staked tokens is zero")

    if pending_rewards == 0:
        return accumulated_rewards_per_share

    reward_delta = pending_rewards * Q64_SCALE
    if reward_delta > MAX_U128:
        raise RewardCalcOverflow("Scaled reward delta exceeded 128-bit boundary")

    normalized_delta = reward_delta // total_staked_tokens

    updated_accum = accumulated_rewards_per_share + normalized_delta
    if updated_accum > MAX_U128:
        raise RewardCalcOverflow("Accumulated rewards per share exceeded 128-bit boundary")

    return updated_accum


def calculate_reward(
    accumulated_rewards_per_share: int,
    staked_tokens: int,
) -> int:
    """Calculates reward payout for a given token balance against a Q64.64 accumulator.

    Args:
        accumulated_rewards_per_share: Current Q64.64 reward accumulator.
        staked_tokens: Staked token balance of the claimant.

    Returns:
        Unsigned integer reward amount to be paid out.

    Raises:
        RewardCalcOverflow: If calculation overflows 128-bit boundary.
    """
    if staked_tokens == 0 or accumulated_rewards_per_share == 0:
        return 0

    hi = accumulated_rewards_per_share >> 64
    lo = accumulated_rewards_per_share & Q64_FRACTIONAL_MASK

    lo_prod = lo * staked_tokens
    hi_prod = hi * staked_tokens

    if lo_prod > MAX_U128 or hi_prod > MAX_U128:
        raise RewardCalcOverflow("Multiplication overflowed 128-bit boundary")

    lo_scaled = lo_prod >> 64
    total = hi_prod + lo_scaled

    if total > MAX_U128:
        raise RewardCalcOverflow("Reward payout addition overflowed 128-bit boundary")

    return total


def checked_mul_q64_64(a: int, b: int) -> int:
    """Multiplies two Q64.64 fixed-point numbers with comprehensive overflow checks.

    Args:
        a: First Q64.64 operand.
        b: Second Q64.64 operand.

    Returns:
        Q64.64 product.

    Raises:
        RewardOverflow: If product exceeds Q64.64 maximum representation.
    """
    hi_a, lo_a = a >> 64, a & Q64_FRACTIONAL_MASK
    hi_b, lo_b = b >> 64, b & Q64_FRACTIONAL_MASK

    p3 = hi_a * hi_b
    if p3 > Q64_FRACTIONAL_MASK:
        raise RewardOverflow("High components multiplication overflows Q64.64")

    mid = (lo_a * hi_b) + (hi_a * lo_b)
    res_lo = ((lo_a * lo_b) >> 64) + ((mid & Q64_FRACTIONAL_MASK) << 64)
    res_hi = p3 + (mid >> 64)

    if res_hi > Q64_FRACTIONAL_MASK:
        raise RewardOverflow("Result upper 64 bits exceeded maximum allowable magnitude")

    total = (res_hi << 64) + res_lo
    if total > MAX_U128:
        raise RewardOverflow("Result exceeded 128-bit limit")
    return total


def checked_div_q64_64(numerator: int, denominator: int) -> int:
    """Divides two Q64.64 fixed-point numbers.

    Args:
        numerator: Q64.64 dividend.
        denominator: Q64.64 divisor.

    Returns:
        Q64.64 quotient.

    Raises:
        RewardCalcDivByZero: If denominator is zero.
        RewardOverflow: If scaling overflows 128-bit boundary.
        RewardUnderflow: If result is invalid.
    """
    if denominator == 0:
        raise RewardCalcDivByZero("Division by zero in Q64.64 division")

    scaled = numerator << 64
    if scaled > (MAX_U128 << 64):
        raise RewardOverflow("Scaling dividend overflowed representation limit")

    res = scaled // denominator
    if res > MAX_U128:
        raise RewardOverflow("Quotient exceeded 128-bit bounds")
    return res


@dataclass
class Pool:
    """Fixed-point staking pool state machine utilizing Q64.64 representation."""

    pool_authority: str
    total_staked_tokens: int = 0
    accumulated_rewards_per_share: int = 0
    last_update_epoch: int = 0
    reward_rate: int = 0
    is_migrated: bool = True

    def accrue_rewards(self, pending_rewards: int) -> int:
        """Accrues pending rewards into the accumulator.

        Args:
            pending_rewards: Amount of reward tokens to distribute.

        Returns:
            Updated accumulated_rewards_per_share.
        """
        updated = accrue_rewards(
            self.accumulated_rewards_per_share,
            self.total_staked_tokens,
            pending_rewards,
        )
        self.accumulated_rewards_per_share = updated
        return updated

    def calculate_reward(self, staked_tokens: int) -> int:
        """Calculates reward payout for a specific stake balance.

        Args:
            staked_tokens: Claimant staked balance.

        Returns:
            Calculated reward token payout.
        """
        return calculate_reward(self.accumulated_rewards_per_share, staked_tokens)

    def calculate_total_rewards(self) -> int:
        """Calculates total pending rewards across all staked tokens in the pool.

        Returns:
            Calculated reward sum.
        """
        return calculate_reward(self.accumulated_rewards_per_share, self.total_staked_tokens)


@dataclass
class VulnerablePool:
    """Legacy vulnerable pool implementation demonstrating 64-bit integer overflow."""

    pool_authority: str
    total_staked_tokens: int = 0
    accumulated_rewards_per_share: int = 0
    last_update_epoch: int = 0
    reward_rate: int = 0

    def calculate_reward_vulnerable(self, staked_tokens: int) -> int:
        """Calculates reward using unscaled 64-bit multiplication.

        Args:
            staked_tokens: Claimant stake balance.

        Returns:
            Raw product mimicking unpatched 64-bit truncation or overflow.

        Raises:
            OverflowError: If raw multiplication exceeds 64-bit unsigned integer limit.
        """
        product = self.accumulated_rewards_per_share * staked_tokens
        if product > MAX_U64:
            raise OverflowError("64-bit integer overflow frozen reward withdrawals")
        return product
