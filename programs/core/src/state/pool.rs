use anchor_lang::prelude::*;

use crate::errors::PoolError;

/// Scale factor for Q64.64 fixed-point arithmetic (2^64).
pub const Q64_SCALE: u128 = 1u128 << 64;

/// Mask isolating the 64 fractional bits of a Q64.64 value.
pub const Q64_FRACTIONAL_MASK: u128 = u64::MAX as u128;

/// Pool-local `Result` alias defaulting to [`PoolError`].
pub type PoolResult<T> = std::result::Result<T, PoolError>;

/// Reward pool state.
///
/// `accumulated_rewards_per_share` is a **Q64.64 fixed-point** value stored in a
/// `u128`. Widening it from the old `u64` (and scaling every operation through
/// the checked helpers below) is what fixes issue #1300: the accumulator can no
/// longer wrap when it is multiplied by the staked balance during long lockup
/// epochs.
#[account]
#[derive(Default, Debug, PartialEq, Eq)]
pub struct Pool {
    pub pool_authority: Pubkey,
    pub total_staked_tokens: u64,
    pub accumulated_rewards_per_share: u128,
    pub last_update_epoch: u64,
    pub reward_rate: u64,
    pub is_migrated: bool,
}

impl Pool {
    /// Serialized account size: 8-byte Anchor discriminator + authority(32) +
    /// total(8) + accum(16) + epoch(8) + rate(8) + flag(1).
    pub const LEN: usize = 8 + 32 + 8 + 16 + 8 + 8 + 1;

    /// Accrues `pending_rewards` into the accumulator and persists it.
    pub fn accrue_rewards(&mut self, pending_rewards: u64) -> PoolResult<u128> {
        let updated = accrue_rewards(
            self.accumulated_rewards_per_share,
            self.total_staked_tokens,
            pending_rewards,
        )?;
        self.accumulated_rewards_per_share = updated;
        Ok(updated)
    }

    /// Reward owed to `staked_tokens` under the current accumulator.
    pub fn calculate_reward(&self, staked_tokens: u64) -> PoolResult<u128> {
        calculate_reward(self.accumulated_rewards_per_share, staked_tokens)
    }

    /// Total rewards accrued across every currently staked token.
    pub fn calculate_total_rewards(&self) -> PoolResult<u128> {
        calculate_reward(
            self.accumulated_rewards_per_share,
            self.total_staked_tokens,
        )
    }
}

/// Widens two operands to `u128` and multiplies with an explicit overflow error.
pub fn checked_mul(a: u128, b: u128) -> PoolResult<u128> {
    a.checked_mul(b).ok_or(PoolError::RewardCalcOverflow)
}

/// `u128` division that maps a zero denominator to a typed error.
pub fn checked_div(numerator: u128, denominator: u128) -> PoolResult<u128> {
    if denominator == 0 {
        return Err(PoolError::RewardCalcDivByZero);
    }
    numerator
        .checked_div(denominator)
        .ok_or(PoolError::RewardCalcOverflow)
}

/// Accrues `pending_rewards` proportionally into a Q64.64 per-share accumulator.
///
/// `delta = pending_rewards * Q64_SCALE / total_staked_tokens`.
///
/// # Errors
/// * [`PoolError::RewardCalcDivByZero`] when nothing is staked.
/// * [`PoolError::RewardCalcOverflow`] when the scaled delta or the resulting
///   accumulator cannot fit a `u128`.
pub fn accrue_rewards(
    accumulated_rewards_per_share: u128,
    total_staked_tokens: u64,
    pending_rewards: u64,
) -> PoolResult<u128> {
    if total_staked_tokens == 0 {
        return Err(PoolError::RewardCalcDivByZero);
    }
    if pending_rewards == 0 {
        return Ok(accumulated_rewards_per_share);
    }

    let scaled = checked_mul(pending_rewards as u128, Q64_SCALE)?;
    let delta = checked_div(scaled, total_staked_tokens as u128)?;

    accumulated_rewards_per_share
        .checked_add(delta)
        .ok_or(PoolError::RewardCalcOverflow)
}

/// Returns the reward owed to `staked_tokens` from a Q64.64 accumulator.
///
/// `reward = accumulated_rewards_per_share * staked_tokens / Q64_SCALE`.
/// The high and low 64-bit halves are reduced separately so a single
/// intermediate product never has to hold the full 192-bit result.
///
/// # Errors
/// [`PoolError::RewardCalcOverflow`] when a product or the final payout
/// exceeds `u128`.
pub fn calculate_reward(
    accumulated_rewards_per_share: u128,
    staked_tokens: u64,
) -> PoolResult<u128> {
    if staked_tokens == 0 || accumulated_rewards_per_share == 0 {
        return Ok(0);
    }

    let tokens = staked_tokens as u128;
    let hi = accumulated_rewards_per_share >> 64;
    let lo = accumulated_rewards_per_share & Q64_FRACTIONAL_MASK;

    let hi_prod = checked_mul(hi, tokens)?;
    let lo_prod = checked_mul(lo, tokens)?;
    let lo_scaled = lo_prod >> 64;

    hi_prod
        .checked_add(lo_scaled)
        .ok_or(PoolError::RewardCalcOverflow)
}

/// Multiplies two Q64.64 values, returning a Q64.64 product.
///
/// Splits each operand into integer/fractional halves so every partial product
/// is range-checked before it is combined.
///
/// # Errors
/// [`PoolError::RewardOverflow`] when the product does not fit a `u128`.
pub fn checked_mul_q64_64(a: u128, b: u128) -> PoolResult<u128> {
    let (hi_a, lo_a) = (a >> 64, a & Q64_FRACTIONAL_MASK);
    let (hi_b, lo_b) = (b >> 64, b & Q64_FRACTIONAL_MASK);

    // a*b = hi_a*hi_b*2^128 + (hi_a*lo_b + lo_a*hi_b)*2^64 + lo_a*lo_b.
    // The Q64.64 product is that expression shifted right by 64:
    //   (hi_a*hi_b) << 64  +  (hi_a*lo_b + lo_a*hi_b)  +  (lo_a*lo_b) >> 64.
    let p_hh = checked_mul(hi_a, hi_b).map_err(|_| PoolError::RewardOverflow)?;
    let high = checked_mul(p_hh, Q64_SCALE).map_err(|_| PoolError::RewardOverflow)?;

    let p_hl = checked_mul(hi_a, lo_b).map_err(|_| PoolError::RewardOverflow)?;
    let p_lh = checked_mul(lo_a, hi_b).map_err(|_| PoolError::RewardOverflow)?;
    let mid = p_hl.checked_add(p_lh).ok_or(PoolError::RewardOverflow)?;

    let low = checked_mul(lo_a, lo_b).map_err(|_| PoolError::RewardOverflow)? >> 64;

    high.checked_add(mid)
        .and_then(|v| v.checked_add(low))
        .ok_or(PoolError::RewardOverflow)
}

/// Divides two Q64.64 values, returning a Q64.64 quotient.
///
/// The result is `floor(numerator * 2^64 / denominator)`. It is built from the
/// integer part plus 64 fractional bits generated by binary long division, so
/// the 64-bit shift never happens on a value that could overflow a u128 — a
/// plain `numerator << 64` silently truncates the top bits.
///
/// # Errors
/// * [`PoolError::RewardCalcDivByZero`] when `denominator` is zero.
/// * [`PoolError::RewardOverflow`] when the integer part alone needs more than
///   64 bits (the quotient is not representable as Q64.64).
pub fn checked_div_q64_64(numerator: u128, denominator: u128) -> PoolResult<u128> {
    if denominator == 0 {
        return Err(PoolError::RewardCalcDivByZero);
    }

    let integer = numerator / denominator;
    let integer_part = checked_mul(integer, Q64_SCALE).map_err(|_| PoolError::RewardOverflow)?;

    let mut remainder = numerator % denominator;
    let mut fractional: u128 = 0;
    for _ in 0..64 {
        fractional <<= 1;
        match remainder.checked_mul(2) {
            Some(doubled) if doubled < denominator => {
                remainder = doubled;
            }
            Some(doubled) => {
                remainder = doubled - denominator;
                fractional |= 1;
            }
            None => {
                // remainder * 2 >= 2^128 > denominator, so a bit is always set
                // and the wrapped difference (which fits u128) is the remainder.
                remainder = remainder.wrapping_mul(2).wrapping_sub(denominator);
                fractional |= 1;
            }
        }
    }

    integer_part
        .checked_add(fractional)
        .ok_or(PoolError::RewardOverflow)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn accrual_is_exact_and_uses_q64_scale() {
        let total_staked: u64 = 10_000_000_000;
        let pending: u64 = 5_000_000_000;

        let accrued = accrue_rewards(0, total_staked, pending).unwrap();
        assert_eq!(accrued, (pending as u128 * Q64_SCALE) / total_staked as u128);
    }

    #[test]
    fn u64_reproduction_overflow_is_now_safe() {
        // The values from the report would wrap u64; the u128 engine does not.
        let accum = 2_000_000_000u128 * Q64_SCALE;
        let staked = 10_000_000_000u64;

        let payout = calculate_reward(accum, staked).unwrap();
        assert_eq!(payout, 2_000_000_000u128 * staked as u128);
    }

    #[test]
    fn zero_stake_accrual_is_div_by_zero() {
        assert_eq!(
            accrue_rewards(100, 0, 1_000).unwrap_err(),
            PoolError::RewardCalcDivByZero
        );
    }

    #[test]
    fn near_max_accumulator_overflows_cleanly() {
        assert_eq!(
            accrue_rewards(u128::MAX - 10, 1_000, 1_000).unwrap_err(),
            PoolError::RewardCalcOverflow
        );
    }

    #[test]
    fn q64_64_mul_and_div_round_trip() {
        let one = Q64_SCALE;
        let two = 2 * Q64_SCALE;
        assert_eq!(checked_mul_q64_64(one, two).unwrap(), two);

        let four = 4 * Q64_SCALE;
        assert_eq!(checked_div_q64_64(four, two).unwrap(), two);
    }

    #[test]
    fn q64_64_extreme_operands_overflow() {
        assert_eq!(
            checked_mul_q64_64(u128::MAX, u128::MAX).unwrap_err(),
            PoolError::RewardOverflow
        );
    }

    #[test]
    fn q64_64_fractional_operands() {
        // Non-zero fractional halves: 1.5 * 1.5 = 2.25 and 1.5 / 0.5 = 3.
        let half = Q64_SCALE / 2;
        let one_point_five = Q64_SCALE + half;
        assert_eq!(
            checked_mul_q64_64(one_point_five, one_point_five).unwrap(),
            9 * Q64_SCALE / 4
        );
        assert_eq!(
            checked_div_q64_64(one_point_five, half).unwrap(),
            3 * Q64_SCALE
        );
    }

    #[test]
    fn q64_64_division_large_denominator() {
        // (2^100 << 64) / 2^127 = 2^37; the intermediate must not overflow.
        assert_eq!(checked_div_q64_64(1 << 100, 1 << 127).unwrap(), 1 << 37);
        // floor(2^64 * 2^64 / (3 * 2^64)) = floor(2^64 / 3).
        assert_eq!(
            checked_div_q64_64(Q64_SCALE, 3 * Q64_SCALE).unwrap(),
            Q64_SCALE / 3
        );
    }

    #[test]
    fn max_u64_boundary_is_representable() {
        let accum = accrue_rewards(0, u64::MAX, u64::MAX).unwrap();
        assert_eq!(accum, Q64_SCALE);
        assert_eq!(calculate_reward(accum, u64::MAX).unwrap(), u64::MAX as u128);
    }
}
