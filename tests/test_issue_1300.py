"""Comprehensive unit and integration test suite for Issue #1300."""

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
from packages.staking_reward_engine.verifier import StakingRewardFormalVerifier


def test_q64_constants_integrity() -> None:
    """Validates bitwise definitions of Q64 constants."""
    assert Q64_SCALE == 1 << 64
    assert Q64_FRACTIONAL_MASK == (1 << 64) - 1
    assert (Q64_SCALE & Q64_FRACTIONAL_MASK) == 0


def test_vulnerability_reproduction_and_fix() -> None:
    """Verifies unpatched 64-bit pool overflows while patched Q64.64 pool succeeds."""
    staked_tokens = 10_000_000_000
    accum_per_share = 2_000_000_000

    vuln_pool = VulnerablePool(
        pool_authority="VulnerableAuthority",
        total_staked_tokens=staked_tokens,
        accumulated_rewards_per_share=accum_per_share,
    )

    with pytest.raises(OverflowError, match="64-bit integer overflow"):
        vuln_pool.calculate_reward_vulnerable(staked_tokens)

    patched_pool = Pool(
        pool_authority="PatchedAuthority",
        total_staked_tokens=staked_tokens,
        accumulated_rewards_per_share=accum_per_share * Q64_SCALE,
    )
    payout = patched_pool.calculate_reward(staked_tokens)
    assert payout == accum_per_share * staked_tokens


def test_accrue_rewards_zero_staked_tokens() -> None:
    """Verifies accrual with zero staked tokens raises RewardCalcDivByZero."""
    with pytest.raises(RewardCalcDivByZero):
        accrue_rewards(0, 0, 5000)


def test_accrue_rewards_zero_pending_rewards() -> None:
    """Verifies accrual with zero pending rewards preserves accumulator."""
    initial_accum = 987_654_321
    res = accrue_rewards(initial_accum, 1_000_000, 0)
    assert res == initial_accum


def test_calculate_reward_zero_staked() -> None:
    """Verifies zero staked tokens produces zero payout."""
    assert calculate_reward(Q64_SCALE * 10, 0) == 0
    assert calculate_reward(0, 10_000_000) == 0


def test_boundary_max_u64_values() -> None:
    """Verifies calculations at maximum 64-bit unsigned bounds."""
    accum = accrue_rewards(0, MAX_U64, MAX_U64)
    assert accum == Q64_SCALE
    payout = calculate_reward(accum, MAX_U64)
    assert payout == MAX_U64


def test_fractional_reward_precision() -> None:
    """Verifies fractional reward distribution conserves total pool supply."""
    pool = Pool(
        pool_authority="AuthorityPDA",
        total_staked_tokens=1_000_000,
        accumulated_rewards_per_share=0,
    )
    pool.accrue_rewards(500_000)

    user1_payout = pool.calculate_reward(333_333)
    user2_payout = pool.calculate_reward(333_333)
    user3_payout = pool.calculate_reward(333_334)

    total_claimed = user1_payout + user2_payout + user3_payout
    assert total_claimed <= 500_000
    assert (500_000 - total_claimed) <= 1


def test_prolonged_epochs_accumulation() -> None:
    """Verifies continuous accrual across hundreds of epochs."""
    pool = Pool(
        pool_authority="AuthorityPDA",
        total_staked_tokens=20_000_000_000,
        accumulated_rewards_per_share=0,
    )

    for _ in range(500):
        pool.accrue_rewards(20_000_000)

    user_stake = 5_000_000_000
    user_payout = pool.calculate_reward(user_stake)
    expected = (20_000_000 * 500) // 4
    assert abs(user_payout - expected) <= 1


def test_u128_overflow_protection() -> None:
    """Verifies 128-bit boundary arithmetic raises RewardCalcOverflow."""
    with pytest.raises(RewardCalcOverflow):
        checked_mul(MAX_U128, 2)

    with pytest.raises(RewardCalcOverflow):
        accrue_rewards(MAX_U128 - 1, 100, 100)


def test_checked_div_zero() -> None:
    """Verifies checked division by zero raises RewardCalcDivByZero."""
    with pytest.raises(RewardCalcDivByZero):
        checked_div(100, 0)


def test_checked_mul_q64_64() -> None:
    """Verifies Q64.64 multiplication and overflow handling."""
    one = Q64_SCALE
    two = 2 * Q64_SCALE
    prod = checked_mul_q64_64(one, two)
    assert prod == two

    with pytest.raises(RewardOverflow):
        checked_mul_q64_64(MAX_U128, MAX_U128)


def test_checked_div_q64_64() -> None:
    """Verifies Q64.64 division and zero division handling."""
    four = 4 * Q64_SCALE
    two = 2 * Q64_SCALE
    quot = checked_div_q64_64(four, two)
    assert quot == two

    with pytest.raises(RewardCalcDivByZero):
        checked_div_q64_64(four, 0)


def test_pool_lifecycle_full() -> None:
    """Verifies complete staking pool lifecycle."""
    pool = Pool(
        pool_authority="PoolAuthority1111111111111111111111111",
        total_staked_tokens=5_000_000,
        accumulated_rewards_per_share=0,
        last_update_epoch=10,
        reward_rate=250,
    )
    assert pool.total_staked_tokens == 5_000_000
    assert pool.accumulated_rewards_per_share == 0

    pool.accrue_rewards(10_000_000)
    assert pool.accumulated_rewards_per_share == 2 * Q64_SCALE

    user_reward = pool.calculate_reward(1_000_000)
    assert user_reward == 2_000_000

    total_pool_rewards = pool.calculate_total_rewards()
    assert total_pool_rewards == 10_000_000


def test_formal_verifier_integration() -> None:
    """Verifies formal verification engine reports 100% theorem satisfaction."""
    verifier = StakingRewardFormalVerifier()
    results = verifier.verify_all()
    assert len(results) == 8
    for inv_name, status in results.items():
        assert status is True, f"Formal invariant failed: {inv_name}"
