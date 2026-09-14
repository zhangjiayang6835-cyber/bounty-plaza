use anchor_lang::prelude::*;
use crate::state::Pool;

/// Accounts required to accrue rewards to a pool.
#[derive(Accounts)]
pub struct AccruePoolRewards<'info> {
    #[account(
        mut,
        has_one = pool_authority
    )]
    pub pool: Account<'info, Pool>,
    pub pool_authority: Signer<'info>,
}

/// Accrues pending rewards into the pool accumulator.
pub fn process_accrue_pool_rewards(
    ctx: Context<AccruePoolRewards>,
    pending_rewards: u64,
) -> Result<()> {
    let pool = &mut ctx.accounts.pool;
    pool.accrue_rewards(pending_rewards)?;
    pool.last_update_epoch = Clock::get()?.epoch;
    Ok(())
}
