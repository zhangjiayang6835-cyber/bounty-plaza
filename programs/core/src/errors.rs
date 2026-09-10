use anchor_lang::prelude::*;

pub use crate::state::pool::PoolError;

/// Error codes returned by the core runtime program.
#[error_code]
pub enum ErrorCode {
    #[msg("Account authority does not match the vault authority PDA.")]
    InvalidAuthority,
    #[msg("Account is not owned by the expected program.")]
    InvalidAccountOwner,
    #[msg("Insufficient liquidity available in the vault.")]
    InsufficientLiquidity,
}
