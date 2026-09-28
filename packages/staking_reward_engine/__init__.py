"""Staking reward accrual engine (Issue #1300).

Public API for the Q64.64 fixed-point reward accumulator that replaces the
overflow-prone u64 arithmetic in ``programs/core/src/state/pool.rs``.
"""

from packages.staking_reward_engine.pool import (
    MAX_U64,
    MAX_U128,
    Q64_FRACTIONAL_MASK,
    Q64_SCALE,
    Pool,
    PoolError,
    RewardCalcDivByZero,
    RewardCalcOverflow,
    RewardCalcUnderflow,
    RewardOverflow,
    RewardUnderflow,
    VulnerablePool,
    accrue_rewards,
    calculate_reward,
    checked_div,
    checked_div_q64_64,
    checked_mul,
    checked_mul_q64_64,
)

__all__ = [
    "MAX_U64",
    "MAX_U128",
    "Q64_FRACTIONAL_MASK",
    "Q64_SCALE",
    "Pool",
    "PoolError",
    "RewardCalcDivByZero",
    "RewardCalcOverflow",
    "RewardCalcUnderflow",
    "RewardOverflow",
    "RewardUnderflow",
    "VulnerablePool",
    "accrue_rewards",
    "calculate_reward",
    "checked_div",
    "checked_div_q64_64",
    "checked_mul",
    "checked_mul_q64_64",
]
