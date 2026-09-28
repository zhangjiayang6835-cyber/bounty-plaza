"""Q64.64 fixed-point staking reward engine — issue #1300 reference port.

The on-chain bug: ``accumulated_rewards_per_share`` (u64) multiplied by
``total_staked_tokens`` (u64) overflows 64 bits during long lockup epochs,
permanently freezing reward withdrawals. The fix widens the accumulator to a
u128 Q64.64 fixed-point value and routes every arithmetic step through explicit
checked helpers that surface a typed error instead of wrapping/panicking.

This module is a faithful Python port of ``programs/core/src/state/pool.rs`` so
the arithmetic can be executed and property-tested off-chain.
"""

from __future__ import annotations

from dataclasses import dataclass

# 64-bit and 128-bit unsigned ceilings.
MAX_U64: int = (1 << 64) - 1
MAX_U128: int = (1 << 128) - 1

# Q64.64 fixed-point layout: 64 integer bits, 64 fractional bits.
Q64_SCALE: int = 1 << 64
Q64_FRACTIONAL_MASK: int = Q64_SCALE - 1


class PoolError(Exception):
    """Base class for every staking reward arithmetic failure."""


class RewardCalcOverflow(PoolError):
    """A 128-bit intermediate or final value exceeded its ceiling."""


class RewardCalcDivByZero(PoolError):
    """A division had a zero denominator."""


class RewardCalcUnderflow(PoolError):
    """A shift or subtraction produced a negative out-of-range value."""


class RewardOverflow(PoolError):
    """A Q64.64 fixed-point product exceeded the representable ceiling."""


class RewardUnderflow(PoolError):
    """A Q64.64 fixed-point quotient fell outside the representable range."""


def checked_mul(a: int, b: int) -> int:
    """Return ``a * b`` guarded against 128-bit overflow.

    Raises:
        RewardCalcOverflow: product exceeds ``MAX_U128`` or an operand is negative.
    """
    if a < 0 or b < 0:
        raise RewardCalcOverflow("negative operand in unsigned multiplication")
    result = a * b
    if result > MAX_U128:
        raise RewardCalcOverflow("multiplication overflowed u128")
    return result


def checked_add(a: int, b: int) -> int:
    """Return ``a + b`` guarded against 128-bit overflow."""
    if a < 0 or b < 0:
        raise RewardCalcOverflow("negative operand in unsigned addition")
    result = a + b
    if result > MAX_U128:
        raise RewardCalcOverflow("addition overflowed u128")
    return result


def checked_div(numerator: int, denominator: int) -> int:
    """Return ``numerator // denominator`` guarding zero and sign.

    Raises:
        RewardCalcDivByZero: ``denominator`` is zero.
        RewardCalcOverflow: an operand is negative.
    """
    if numerator < 0 or denominator < 0:
        raise RewardCalcOverflow("negative operand in unsigned division")
    if denominator == 0:
        raise RewardCalcDivByZero("division by zero")
    return numerator // denominator


def _mul_shr_64(a: int, b: int) -> int:
    """Exact ``(a * b) >> 64`` computed with unbounded intermediates.

    Exactness matters: splitting the operands (the C-style trick) only avoids
    overflow by truncating the low 64 bits of ``a * b``, which is fine for
    invariant checks but wrong for the full-precision accumulator. Python's
    arbitrary-precision integers let us keep the mathematically exact result and
    raise only when the *final* value cannot fit a u128.
    """
    if a < 0 or b < 0:
        raise RewardOverflow("negative operand in fixed-point multiply")
    return (a * b) >> 64


def accrue_rewards(
    accumulated_rewards_per_share: int,
    total_staked_tokens: int,
    pending_rewards: int,
) -> int:
    """Fold ``pending_rewards`` into the Q64.64 per-share accumulator.

    ``delta = pending_rewards * Q64_SCALE / total_staked_tokens`` distributes the
    newly accrued rewards proportionally across every staked token.

    Raises:
        RewardCalcDivByZero: no tokens staked.
        RewardCalcOverflow: the scaled delta or the new accumulator exceeds u128.
    """
    if accumulated_rewards_per_share < 0:
        raise RewardCalcOverflow("negative accumulator")
    if total_staked_tokens == 0:
        raise RewardCalcDivByZero("cannot accrue rewards with zero stake")
    if pending_rewards == 0:
        return accumulated_rewards_per_share

    scaled = checked_mul(pending_rewards, Q64_SCALE)
    delta = scaled // total_staked_tokens
    return checked_add(accumulated_rewards_per_share, delta)


def calculate_reward(
    accumulated_rewards_per_share: int,
    staked_tokens: int,
) -> int:
    """Return the reward owed to ``staked_tokens`` under a Q64.64 accumulator.

    ``reward = accumulated_rewards_per_share * staked_tokens / Q64_SCALE`` is
    evaluated exactly and then range-checked against u128.

    Raises:
        RewardCalcOverflow: the payout cannot fit a u128.
    """
    if accumulated_rewards_per_share < 0 or staked_tokens < 0:
        raise RewardCalcOverflow("negative operand in reward calculation")
    if staked_tokens == 0 or accumulated_rewards_per_share == 0:
        return 0

    payout = (accumulated_rewards_per_share * staked_tokens) >> 64
    if payout > MAX_U128:
        raise RewardCalcOverflow("reward payout overflowed u128")
    return payout


def checked_mul_q64_64(a: int, b: int) -> int:
    """Multiply two Q64.64 numbers, returning a Q64.64 product.

    Raises:
        RewardOverflow: the product does not fit a u128 Q64.64 value.
    """
    result = _mul_shr_64(a, b)
    if result > MAX_U128:
        raise RewardOverflow("Q64.64 product overflowed u128")
    return result


def checked_div_q64_64(numerator: int, denominator: int) -> int:
    """Divide two Q64.64 numbers, returning a Q64.64 quotient.

    Raises:
        RewardCalcDivByZero: ``denominator`` is zero.
        RewardOverflow: the scaled dividend or the quotient exceeds u128.
    """
    if numerator < 0 or denominator < 0:
        raise RewardOverflow("negative operand in Q64.64 division")
    if denominator == 0:
        raise RewardCalcDivByZero("division by zero in Q64.64 division")

    quotient = (numerator << 64) // denominator
    if quotient > MAX_U128:
        raise RewardOverflow("Q64.64 quotient overflowed u128")
    return quotient


@dataclass
class Pool:
    """Staking pool whose accumulator uses Q64.64 fixed-point math."""

    pool_authority: str
    total_staked_tokens: int = 0
    accumulated_rewards_per_share: int = 0
    last_update_epoch: int = 0
    reward_rate: int = 0
    is_migrated: bool = True

    def accrue_rewards(self, pending_rewards: int) -> int:
        """Accrue rewards and persist the updated accumulator."""
        updated = accrue_rewards(
            self.accumulated_rewards_per_share,
            self.total_staked_tokens,
            pending_rewards,
        )
        self.accumulated_rewards_per_share = updated
        return updated

    def calculate_reward(self, staked_tokens: int) -> int:
        """Reward owed to a single staker for ``staked_tokens``."""
        return calculate_reward(self.accumulated_rewards_per_share, staked_tokens)

    def calculate_total_rewards(self) -> int:
        """Total rewards distributed across all currently staked tokens."""
        return calculate_reward(
            self.accumulated_rewards_per_share, self.total_staked_tokens
        )


class VulnerablePool:
    """Pre-fix u64 engine, kept for regression/reproduction tests only.

    This mirrors the buggy on-chain arithmetic: a u64 accumulator multiplied by
    a u64 stake, which overflows and permanently freezes payouts.
    """

    def __init__(
        self,
        pool_authority: str,
        total_staked_tokens: int = 0,
        accumulated_rewards_per_share: int = 0,
    ) -> None:
        self.pool_authority = pool_authority
        self.total_staked_tokens = total_staked_tokens
        self.accumulated_rewards_per_share = accumulated_rewards_per_share

    def calculate_reward_vulnerable(self, staked_tokens: int) -> int:
        """Reproduce the u64 overflow; raise ``OverflowError`` when it wraps."""
        product = self.accumulated_rewards_per_share * staked_tokens
        if product > MAX_U64:
            raise OverflowError(
                "64-bit integer overflow in reward accrual: product "
                f"{product} exceeds u64 max {MAX_U64}"
            )
        return product
