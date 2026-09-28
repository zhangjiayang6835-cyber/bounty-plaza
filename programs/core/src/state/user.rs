use anchor_lang::prelude::*;

#[account]
pub struct User {
    pub pending_rewards: u128,
    // ... other fields
}
