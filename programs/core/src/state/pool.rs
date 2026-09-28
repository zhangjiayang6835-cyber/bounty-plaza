use anchor_lang::prelude::*;

#[account]
pub struct Pool {
    pub accumulated_rewards_per_share: u128,
    // ... other fields
}
