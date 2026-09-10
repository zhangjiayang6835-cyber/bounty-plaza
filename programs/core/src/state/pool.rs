use anchor_lang::prelude::*;

/// Scale factor for Q64.64 fixed-point arithmetic (2^64).
pub const Q64_SCALE: u128 = 1u128 << 64;

/// Bitmask for isolating the fractional 64-bit component.
pub const Q64_FRACTIONAL_MASK: u128 = u64::MAX as u128;

/// Error codes specific to staking pool operations and reward calculations.
#[error_code]
#[derive(Eq, PartialEq)]
pub enum PoolError {
    #[msg("Reward calculation overflow")]
    RewardCalcOverflow,
    #[msg("Reward calculation division by zero")]
    RewardCalcDivByZero,
    #[msg("Reward calculation underflow")]
    RewardCalcUnderflow,
    #[msg("Arithmetic overflow while calculating rewards")]
    RewardOverflow,
    #[msg("Arithmetic underflow while calculating rewards")]
    RewardUnderflow,
}

/// Specialized Result type for pool operations defaulting to PoolError.
pub type Result<T, E = PoolError> = std::result::Result<T, E>;

/// State account representing a staking reward pool.
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
    pub const LEN: usize = 32 + 8 + 16 + 8 + 8 + 1;

    /// Accrues pending rewards into the accumulator using Q64.64 fixed-point math.
    pub fn accrue_rewards(&mut self, pending_rewards: u64) -> Result<u128, PoolError> {
        let updated = accrue_rewards(
            self.accumulated_rewards_per_share,
            self.total_staked_tokens,
            pending_rewards,
        )?;
        self.accumulated_rewards_per_share = updated;
        Ok(updated)
    }

    /// Calculates reward payout for a given token balance using Q64.64 fixed-point math.
    pub fn calculate_reward(&self, staked_tokens: u64) -> Result<u128, PoolError> {
        calculate_reward(self.accumulated_rewards_per_share, staked_tokens)
    }

    /// Calculates total rewards accrued across all currently staked tokens.
    pub fn calculate_total_rewards(&self) -> Result<u128, PoolError> {
        calculate_reward(self.accumulated_rewards_per_share, self.total_staked_tokens)
    }
}

/// Accrues rewards to the accumulator using Q64.64 fixed-point representation.
pub fn accrue_rewards(
    accumulated_rewards_per_share: u128,
    total_staked_tokens: u64,
    pending_rewards: u64,
) -> Result<u128, PoolError> {
    if total_staked_tokens == 0 {
        return Err(PoolError::RewardCalcDivByZero);
    }

    if pending_rewards == 0 {
        return Ok(accumulated_rewards_per_share);
    }

    let total_pool_value = total_staked_tokens as u128;
    let pending_u128 = pending_rewards as u128;

    let reward_delta = pending_u128
        .checked_mul(Q64_SCALE)
        .ok_or(PoolError::RewardCalcOverflow)?;

    let normalized_delta = reward_delta
        .checked_div(total_pool_value)
        .ok_or(PoolError::RewardCalcOverflow)?;

    accumulated_rewards_per_share
        .checked_add(normalized_delta)
        .ok_or(PoolError::RewardCalcOverflow)
}

/// Calculates reward payout for a specific token balance against a Q64.64 accumulator.
pub fn calculate_reward(
    accumulated_rewards_per_share: u128,
    staked_tokens: u64,
) -> Result<u128, PoolError> {
    if staked_tokens == 0 || accumulated_rewards_per_share == 0 {
        return Ok(0);
    }

    let tokens = staked_tokens as u128;
    let hi = accumulated_rewards_per_share >> 64;
    let lo = accumulated_rewards_per_share & Q64_FRACTIONAL_MASK;

    let lo_prod = lo
        .checked_mul(tokens)
        .ok_or(PoolError::RewardCalcOverflow)?;
    let hi_prod = hi
        .checked_mul(tokens)
        .ok_or(PoolError::RewardCalcOverflow)?;

    let lo_scaled = lo_prod >> 64;

    hi_prod
        .checked_add(lo_scaled)
        .ok_or(PoolError::RewardCalcOverflow)
}

/// Multiplies two u128 values with checked overflow detection.
pub fn checked_mul(a: u128, b: u128) -> Result<u128, PoolError> {
    a.checked_mul(b).ok_or(PoolError::RewardCalcOverflow)
}

/// Divides two u128 values with checked division-by-zero detection.
pub fn checked_div(numerator: u128, denominator: u128) -> Result<u128, PoolError> {
    if denominator == 0 {
        return Err(PoolError::RewardCalcDivByZero);
    }
    numerator
        .checked_div(denominator)
        .ok_or(PoolError::RewardCalcOverflow)
}

/// Multiplies two Q64.64 fixed-point numbers, returning a Q64.64 fixed-point product.
pub fn checked_mul_q64_64(a: u128, b: u128) -> Result<u128, PoolError> {
    let hi_a = a >> 64;
    let lo_a = a & Q64_FRACTIONAL_MASK;
    let hi_b = b >> 64;
    let lo_b = b & Q64_FRACTIONAL_MASK;

    let p0 = lo_a
        .checked_mul(lo_b)
        .ok_or(PoolError::RewardOverflow)?;
    let p1 = lo_a
        .checked_mul(hi_b)
        .ok_or(PoolError::RewardOverflow)?;
    let p2 = hi_a
        .checked_mul(lo_b)
        .ok_or(PoolError::RewardOverflow)?;
    let p3 = hi_a
        .checked_mul(hi_b)
        .ok_or(PoolError::RewardOverflow)?;

    if p3 > Q64_FRACTIONAL_MASK {
        return Err(PoolError::RewardOverflow);
    }

    let mid = p1
        .checked_add(p2)
        .ok_or(PoolError::RewardOverflow)?;
    let mid_lo = (mid & Q64_FRACTIONAL_MASK) << 64;
    let mid_hi = mid >> 64;

    let res_lo = (p0 >> 64)
        .checked_add(mid_lo)
        .ok_or(PoolError::RewardOverflow)?;
    let res_hi = p3
        .checked_add(mid_hi)
        .ok_or(PoolError::RewardOverflow)?;

    if res_hi > Q64_FRACTIONAL_MASK {
        return Err(PoolError::RewardOverflow);
    }

    (res_hi << 64)
        .checked_add(res_lo)
        .ok_or(PoolError::RewardOverflow)
}

/// Divides a Q64.64 numerator by a Q64.64 denominator, returning a Q64.64 result.
pub fn checked_div_q64_64(numerator: u128, denominator: u128) -> Result<u128, PoolError> {
    if denominator == 0 {
        return Err(PoolError::RewardCalcDivByZero);
    }

    let scaled_num = numerator
        .checked_shl(64)
        .ok_or(PoolError::RewardOverflow)?;

    scaled_num
        .checked_div(denominator)
        .ok_or(PoolError::RewardUnderflow)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    pub fn test_reward_accrual_overflow_boundaries() {
        let initial_accum: u128 = 0;
        let total_staked: u64 = 10_000_000_000;
        let pending_rewards: u64 = 5_000_000_000;

        let delta = accrue_rewards(initial_accum, total_staked, pending_rewards);
        assert!(delta.is_ok());
        let expected_delta = (pending_rewards as u128 * Q64_SCALE) / (total_staked as u128);
        assert_eq!(delta.unwrap(), expected_delta);

        let large_accum: u128 = (u64::MAX as u128) + 1_000_000;
        let large_staked: u64 = u64::MAX;
        let reward_result = calculate_reward(large_accum, large_staked);
        assert!(reward_result.is_ok());
        let calculated = reward_result.unwrap();
        assert!(calculated > 0);

        let near_max_accum: u128 = u128::MAX - 10;
        let overflow_attempt = accrue_rewards(near_max_accum, 1_000, 1_000);
        assert!(overflow_attempt.is_err());
        assert_eq!(overflow_attempt.unwrap_err(), PoolError::RewardCalcOverflow);

        let zero_staked_attempt = accrue_rewards(100, 0, 1_000);
        assert!(zero_staked_attempt.is_err());
        assert_eq!(
            zero_staked_attempt.unwrap_err(),
            PoolError::RewardCalcDivByZero
        );
    }

    #[test]
    pub fn test_q64_64_checked_mul_div() {
        let a: u128 = 1_000u128 << 64;
        let b: u128 = 500u128;
        let expected: u128 = 500_000u128;
        let mul_result = calculate_reward(a, b as u64);
        assert!(mul_result.is_ok());
        assert_eq!(mul_result.unwrap(), expected);

        let div_zero = checked_div(100, 0);
        assert!(div_zero.is_err());
        assert_eq!(div_zero.unwrap_err(), PoolError::RewardCalcDivByZero);

        let div_valid = checked_div(1_000_000, 250);
        assert!(div_valid.is_ok());
        assert_eq!(div_valid.unwrap(), 4_000);

        let mul_overflow = checked_mul(u128::MAX, 2);
        assert!(mul_overflow.is_err());
        assert_eq!(mul_overflow.unwrap_err(), PoolError::RewardCalcOverflow);
    }

    #[test]
    pub fn test_pool_lifecycle_and_accrual() {
        let mut pool = Pool {
            pool_authority: Pubkey::new_unique(),
            total_staked_tokens: 1_000_000,
            accumulated_rewards_per_share: 0,
            last_update_epoch: 1,
            reward_rate: 100,
            is_migrated: true,
        };

        let accrue_res = pool.accrue_rewards(1_000_000);
        assert!(accrue_res.is_ok());
        assert_eq!(pool.accumulated_rewards_per_share, Q64_SCALE);

        let user_stake: u64 = 250_000;
        let user_reward = pool.calculate_reward(user_stake);
        assert!(user_reward.is_ok());
        assert_eq!(user_reward.unwrap(), 250_000);

        let total_reward = pool.calculate_total_rewards();
        assert!(total_reward.is_ok());
        assert_eq!(total_reward.unwrap(), 1_000_000);

        let fractional_accrue = pool.accrue_rewards(100_000);
        assert!(fractional_accrue.is_ok());
        let fractional_reward = pool.calculate_reward(user_stake);
        assert!(fractional_reward.is_ok());
        assert_eq!(fractional_reward.unwrap(), 274_999);
    }

    #[test]
    pub fn test_boundary_max_u64_staked() {
        let mut pool = Pool {
            pool_authority: Pubkey::new_unique(),
            total_staked_tokens: u64::MAX,
            accumulated_rewards_per_share: 0,
            last_update_epoch: 100,
            reward_rate: 50,
            is_migrated: true,
        };

        let accrue_res = pool.accrue_rewards(u64::MAX);
        assert!(accrue_res.is_ok());
        assert_eq!(pool.accumulated_rewards_per_share, Q64_SCALE);

        let reward = pool.calculate_total_rewards();
        assert!(reward.is_ok());
        assert_eq!(reward.unwrap(), u64::MAX as u128);
    }

    #[test]
    pub fn test_zero_staked_tokens_div_by_zero() {
        let res = accrue_rewards(0, 0, 100);
        assert_eq!(res, Err(PoolError::RewardCalcDivByZero));
    }

    #[test]
    pub fn test_prolonged_lockup_multiple_epochs() {
        let mut pool = Pool {
            pool_authority: Pubkey::new_unique(),
            total_staked_tokens: 50_000_000_000,
            accumulated_rewards_per_share: 0,
            last_update_epoch: 1,
            reward_rate: 1_000,
            is_migrated: true,
        };

        for _ in 0..100 {
            let res = pool.accrue_rewards(50_000_000);
            assert!(res.is_ok());
        }

        let user_stake: u64 = 10_000_000_000;
        let reward = pool.calculate_reward(user_stake);
        assert!(reward.is_ok());
        let val = reward.unwrap();
        assert!(val == 999_999_999 || val == 1_000_000_000);
    }

    #[test]
    pub fn test_zero_pending_rewards_no_change() {
        let initial_accum: u128 = 12345;
        let res = accrue_rewards(initial_accum, 1_000_000, 0);
        assert!(res.is_ok());
        assert_eq!(res.unwrap(), initial_accum);
    }
}
