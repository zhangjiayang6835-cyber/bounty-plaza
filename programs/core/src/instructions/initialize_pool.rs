use anchor_lang::prelude::*;
use crate::state::Pool;

/// Accounts required to initialize a staking reward pool.
#[derive(Accounts)]
pub struct InitializePool<'info> {
    #[account(
        init,
        payer = payer,
        space = 8 + Pool::LEN
    )]
    pub pool: Account<'info, Pool>,
    /// CHECK: Pool authority account
    pub pool_authority: AccountInfo<'info>,
    #[account(mut)]
    pub payer: Signer<'info>,
    pub system_program: Program<'info, System>,
}

/// Initializes a staking pool account with zero initial accumulator.
pub fn init_pool(
    ctx: Context<InitializePool>,
    reward_rate: u64,
) -> Result<()> {
    let pool = &mut ctx.accounts.pool;
    pool.pool_authority = ctx.accounts.pool_authority.key();
    pool.total_staked_tokens = 0;
    pool.accumulated_rewards_per_share = 0;
    pool.last_update_epoch = Clock::get()?.epoch;
    pool.reward_rate = reward_rate;
    pool.is_migrated = true;
    Ok(())
}
