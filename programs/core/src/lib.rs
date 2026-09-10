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
}
