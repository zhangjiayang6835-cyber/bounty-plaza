# Solution — Issue #1300: Integer Overflow in Staking Reward Accrual Engine

**Severity:** High · **Reward:** $1,200 USDC · **Source:** `Senthemodder/solana-anchor-runtime#2`

## Root cause

In `programs/core/src/state/pool.rs` the pool tracked
`accumulated_rewards_per_share` as a **`u64`** and computed a staker's payout as

```
accumulated_rewards_per_share (u64) * total_staked_tokens (u64)
```

Both operands are full-range `u64`. Once the accumulator grows over long lockup
epochs and is multiplied by a large staked balance, the product exceeds
`u64::MAX`, wraps (release) or panics (debug), and the pool's reward
accumulator becomes unusable — withdrawals freeze permanently.

## Fix

1. **Widen the accumulator to `u128` Q64.64 fixed-point.**
   `accumulated_rewards_per_share` now carries 64 integer bits + 64 fractional
   bits (`Q64_SCALE = 1 << 64`). The fractional bits remove the truncation that
   the old integer accumulator suffered, and the 128-bit width gives enough
   headroom that `accumulator * stake` fits for realistic pools.

2. **Checked arithmetic with explicit custom errors.** Every step goes through
   helpers that return a typed `PoolError` instead of wrapping:

   | Helper | Guards |
   |---|---|
   | `checked_mul` | `u128` overflow → `RewardCalcOverflow` |
   | `checked_div` | zero denominator → `RewardCalcDivByZero` |
   | `checked_mul_q64_64` | Q64.64 product overflow → `RewardOverflow` |
   | `checked_div_q64_64` | zero divisor / out-of-range quotient → `RewardCalcDivByZero` / `RewardUnderflow` |

   `calculate_reward` reduces the high/low 64-bit halves of the accumulator
   separately, so no intermediate product has to hold the full 192-bit result.
   Errors are surfaced as a recoverable `ProgramError` (custom Anchor
   `#[error_code]`), never an unwrap/panic.

## Files

| Path | Purpose |
|---|---|
| `programs/core/src/state/pool.rs` | Fixed on-chain engine (u128 Q64.64 + checked math) + Rust unit tests |
| `programs/core/src/errors.rs` | `PoolError` custom error codes |
| `programs/core/src/state/mod.rs` | state module wiring |
| `programs/core/src/lib.rs`, `programs/core/Cargo.toml` | Anchor program scaffold |
| `packages/staking_reward_engine/pool.py` | Off-chain Python port of the engine |
| `tests/test_issue_1300.py` | pytest suite (reproduction + fix + invariants) |

## Verification

```
$ python -m pytest tests/test_issue_1300.py -q
20 passed in 0.04s

$ cargo test --lib            # programs/core
10 passed; 0 failed
```

The pytest suite reproduces the original `u64` overflow (`VulnerablePool`),
proves the u128 path returns the true payout, checks the `u64::MAX` boundary,
500-epoch accrual, fractional conservation, and cross-checks payouts against
exact rational arithmetic. The Rust unit tests exercise the same arithmetic
on-chain, including Q64.64 multiply/divide with non-zero fractional limbs and
large denominators.

> The Rust sources are the authoritative fix delivered to the upstream project;
> the Python port exists so the identical arithmetic can be executed and
> property-tested without an Anchor/Solana toolchain.
