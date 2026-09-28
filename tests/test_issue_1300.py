"""Pytest suite for issue #1300 — u64 reward-accrual overflow -> u128 Q64.64.

Runs the off-chain port in ``packages/staking_reward_engine``. The port mirrors
``programs/core/src/state/pool.rs``, so a green run here exercises the same
arithmetic the on-chain fix performs.
"""

from fractions import Fraction

import pytest

from packages.staking_reward_engine.pool import (
    MAX_U64,
    MAX_U128,
    Q64_FRACTIONAL_MASK,
    Q64_SCALE,
    Pool,
    RewardCalcDivByZero,
    RewardCalcOverflow,
    RewardOverflow,
    VulnerablePool,
    accrue_rewards,
    calculate_reward,
    checked_div,
    checked_div_q64_64,
    checked_mul,
    checked_mul_q64_64,
)


def test_q64_constants_integrity() -> None:
    """Q64 constants partition the value space cleanly."""
    assert Q64_SCALE == 1 << 64
    assert Q64_FRACTIONAL_MASK == (1 << 64) - 1
    assert (Q64_SCALE & Q64_FRACTIONAL_MASK) == 0
    assert MAX_U64 == (1 << 64) - 1
    assert MAX_U128 == (1 << 128) - 1


def test_vulnerability_reproduction_and_fix() -> None:
    """The old u64 path wraps; the u128 Q64.64 path returns the true payout."""
    staked_tokens = 10_000_000_000
    accum_per_share = 2_000_000_000

    vuln = VulnerablePool(
        "VulnerableAuthority",
        total_staked_tokens=staked_tokens,
        accumulated_rewards_per_share=accum_per_share,
    )
    with pytest.raises(OverflowError, match="64-bit integer overflow"):
        vuln.calculate_reward_vulnerable(staked_tokens)

    fixed = Pool(
        "PatchedAuthority",
        total_staked_tokens=staked_tokens,
        accumulated_rewards_per_share=accum_per_share * Q64_SCALE,
    )
    assert fixed.calculate_reward(staked_tokens) == accum_per_share * staked_tokens


def test_accrue_rewards_zero_staked_tokens() -> None:
    """Accruing with no stake is a division-by-zero, not a silent freeze."""
    with pytest.raises(RewardCalcDivByZero):
        accrue_rewards(0, 0, 5_000)


def test_accrue_rewards_zero_pending_rewards() -> None:
    """A zero-reward epoch leaves the accumulator untouched."""
    initial = 987_654_321
    assert accrue_rewards(initial, 1_000_000, 0) == initial


def test_calculate_reward_zero_inputs() -> None:
    """Zero stake or zero accumulator yields zero, never an error."""
    assert calculate_reward(Q64_SCALE * 10, 0) == 0
    assert calculate_reward(0, 10_000_000) == 0


def test_boundary_max_u64_values() -> None:
    """The largest u64 stake/accumulator pair stays representable in u128."""
    accum = accrue_rewards(0, MAX_U64, MAX_U64)
    assert accum == Q64_SCALE
    assert calculate_reward(accum, MAX_U64) == MAX_U64


def test_fractional_reward_precision() -> None:
    """Fractional accrual conserves the distributed total within 1 token."""
    pool = Pool("AuthorityPDA", total_staked_tokens=1_000_000)
    pool.accrue_rewards(500_000)

    total = (
        pool.calculate_reward(333_333)
        + pool.calculate_reward(333_333)
        + pool.calculate_reward(333_334)
    )
    assert total <= 500_000
    assert (500_000 - total) <= 1


def test_prolonged_epochs_accumulation() -> None:
    """500 lockup epochs of accrual do not overflow and stay accurate."""
    pool = Pool("AuthorityPDA", total_staked_tokens=20_000_000_000)
    for _ in range(500):
        pool.accrue_rewards(20_000_000)

    payout = pool.calculate_reward(5_000_000_000)
    expected = (20_000_000 * 500) // 4
    assert abs(payout - expected) <= 1


def test_u128_overflow_protection() -> None:
    """128-bit overflow and accumulator saturation raise explicit errors."""
    with pytest.raises(RewardCalcOverflow):
        checked_mul(MAX_U128, 2)
    with pytest.raises(RewardCalcOverflow):
        accrue_rewards(MAX_U128 - 1, 100, 100)


def test_checked_div_zero() -> None:
    """Checked u128 division rejects a zero denominator."""
    with pytest.raises(RewardCalcDivByZero):
        checked_div(100, 0)


def test_checked_mul_q64_64() -> None:
    """Q64.64 multiplication is correct and overflow-guarded."""
    one = Q64_SCALE
    two = 2 * Q64_SCALE
    assert checked_mul_q64_64(one, two) == two
    with pytest.raises(RewardOverflow):
        checked_mul_q64_64(MAX_U128, MAX_U128)


def test_checked_div_q64_64() -> None:
    """Q64.64 division is correct and rejects a zero divisor."""
    four = 4 * Q64_SCALE
    two = 2 * Q64_SCALE
    assert checked_div_q64_64(four, two) == two
    with pytest.raises(RewardCalcDivByZero):
        checked_div_q64_64(four, 0)


def test_q64_64_fractional_operands() -> None:
    """Non-zero fractional halves exercise both halves of the operands."""
    half = Q64_SCALE // 2
    one_point_five = Q64_SCALE + half
    assert checked_mul_q64_64(one_point_five, one_point_five) == 9 * Q64_SCALE // 4
    assert checked_div_q64_64(one_point_five, half) == 3 * Q64_SCALE


def test_checked_div_q64_64_large_denominator() -> None:
    """Division with a denominator > 2^64 must not overflow early."""
    assert checked_div_q64_64(1 << 100, 1 << 127) == 1 << 37
    assert checked_div_q64_64(Q64_SCALE, 3 * Q64_SCALE) == Q64_SCALE // 3


def test_pool_lifecycle_full() -> None:
    """End-to-end accrual, single-staker payout and pool total."""
    pool = Pool(
        "PoolAuthority1111111111111111111111111",
        total_staked_tokens=5_000_000,
        last_update_epoch=10,
        reward_rate=250,
    )
    assert pool.accumulated_rewards_per_share == 0

    pool.accrue_rewards(10_000_000)
    assert pool.accumulated_rewards_per_share == 2 * Q64_SCALE
    assert pool.calculate_reward(1_000_000) == 2_000_000
    assert pool.calculate_total_rewards() == 10_000_000


@pytest.mark.parametrize(
    "accum,stake",
    [
        (1, 1),
        (Q64_SCALE, 7),
        (3 * Q64_SCALE + 12345, 999_999),
        (MAX_U64 * Q64_SCALE, 1),
        ((1 << 100), (1 << 40) - 7),
    ],
)
def test_calculate_reward_matches_exact_rational_math(accum: int, stake: int) -> None:
    """Payout equals floor(accum * stake / 2**64) computed as an exact Fraction."""
    expected = (Fraction(accum) * stake / Q64_SCALE).__floor__()
    assert calculate_reward(accum, stake) == expected
