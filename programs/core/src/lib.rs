//! Solana Anchor core program — staking reward pool.
//!
//! Issue #1300: the reward accumulator was a `u64` scaled by the staked token
//! balance, which overflowed after long lockup epochs. The accumulator is now a
//! `u128` Q64.64 fixed-point value and every arithmetic step is checked.

use anchor_lang::prelude::*;

pub mod errors;
pub mod state;

declare_id!("Fg6PaFpoGXkYsidMpWTK6W2BeZ7FEfcYkg476zPFsLnS");

#[program]
pub mod core {
    use super::*;

    /// Accrues `pending_rewards` into the pool's Q64.64 accumulator.
    pub fn accrue_rewards(
        ctx: Context<AccrueRewards>,
        pending_rewards: u64,
    ) -> Result<u128> {
        let pool = &mut ctx.accounts.pool;
        Ok(pool.accrue_rewards(pending_rewards)?)
    }

    /// Returns the reward currently owed to `staked_tokens`.
    pub fn calculate_reward(
        ctx: Context<CalculateReward>,
        staked_tokens: u64,
    ) -> Result<u128> {
        Ok(ctx.accounts.pool.calculate_reward(staked_tokens)?)
    }
}

#[derive(Accounts)]
pub struct AccrueRewards<'info> {
    pub pool_authority: Signer<'info>,
    #[account(mut, has_one = pool_authority)]
    pub pool: Account<'info, state::Pool>,
}

#[derive(Accounts)]
pub struct CalculateReward<'info> {
    pub pool: Account<'info, state::Pool>,
}
