use anchor_lang::prelude::*;
use crate::{ErrorCode, checked_mul, checked_shr};

pub fn withdraw_rewards(ctx: Context<WithdrawRewards>) -> ProgramResult {
    let user = &mut ctx.accounts.user;
    let pool = &ctx.accounts.pool;

    let user_staked_amount = user.staked_amount as u128;
    let rewards = checked_mul(user_staked_amount, pool.accumulated_rewards_per_share)?;
    let final_rewards = checked_shr(rewards, 64)?;

    user.pending_rewards = final_rewards.try_into().map_err(|_| ErrorCode::MathOverflow.into())?;

    Ok(())
}
