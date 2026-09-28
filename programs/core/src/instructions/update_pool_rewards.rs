use anchor_lang::prelude::*;
use crate::{ErrorCode, checked_shl, checked_div};

pub fn update_pool_rewards(ctx: Context<UpdatePoolRewards>, reward_amount: u64) -> ProgramResult {
    let pool = &mut ctx.accounts.pool;
    let total_staked_tokens = ctx.accounts.pool.total_staked_tokens;

    if reward_amount == 0 {
        return Ok(());
    }

    if total_staked_tokens == 0 {
        return Err(ErrorCode::MathOverflow.into());
    }

    let reward_amount_u128 = reward_amount as u128;
    let shifted_reward = checked_shl(reward_amount_u128, 64)?;
    let rewards_per_share = checked_div(shifted_reward, total_staked_tokens as u128)?;
    pool.accumulated_rewards_per_share = pool.accumulated_rewards_per_share.checked_add(rewards_per_share).ok_or(ErrorCode::MathOverflow.into())?;

    Ok(())
}
