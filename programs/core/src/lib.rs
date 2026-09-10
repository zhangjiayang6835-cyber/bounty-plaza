use anchor_lang::prelude::*;

pub mod errors;
pub mod instructions;
pub mod state;

pub use errors::ErrorCode;
pub use instructions::*;
pub use state::*;

declare_id!("Fg6PaFpoGXkYsidMpWTK6W2BeZ7FEfcYkg476zPFsLnS");

/// Program entrypoint and instruction handlers.
#[program]
pub mod core {
    use super::*;

    /// Initializes a vault state account with specified initial liquidity and PDA authority.
    pub fn initialize_vault(
        ctx: Context<InitializeVault>,
        total_liquidity: u64,
    ) -> Result<()> {
        instructions::initialize_vault::init_vault(ctx, total_liquidity)
    }

    /// Dispatches cross-program routing with account ownership and has_one authority validations.
    pub fn cpi_dispatch(
        ctx: Context<DispatchCpi>,
        amount: u64,
    ) -> Result<()> {
        instructions::dispatcher::dispatch_cpi(ctx, amount)
    }

    /// Initializes a staking pool with the designated reward rate.
    pub fn initialize_pool(
        ctx: Context<InitializePool>,
        reward_rate: u64,
    ) -> Result<()> {
        instructions::initialize_pool::init_pool(ctx, reward_rate)
    }

    /// Accrues pending rewards into the pool accumulator using Q64.64 fixed-point math.
    pub fn accrue_pool_rewards(
        ctx: Context<AccruePoolRewards>,
        pending_rewards: u64,
    ) -> Result<()> {
        instructions::pool_rewards::process_accrue_pool_rewards(ctx, pending_rewards)
    }
}
