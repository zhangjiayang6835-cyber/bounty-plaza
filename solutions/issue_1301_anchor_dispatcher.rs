//! Production Solana Anchor Dispatcher with Strict Account Ownership & PDA Validation
//! Fixes Critical Bounty #1301: Missing Account Ownership Validation in Anchor CPI Dispatcher.

use anchor_lang::prelude::*;
use anchor_spl::token::{self, Mint, Token, TokenAccount, Transfer};

declare_id!("Disp1atcher11111111111111111111111111111111");

#[program]
pub mod anchor_dispatcher {
    use super::*;

    /// Dispatches liquidity minting and cross-program invocation after verifying
    /// strict ownership, PDA authority seeds, and account invariants.
    pub fn dispatch_liquidity(ctx: Context<DispatchLiquidity>, amount: u64) -> Result<()> {
        require!(amount > 0, DispatcherError::ZeroAmount);

        // Security Validation: Verify state account ownership and program ID match
        require_keys_eq!(
            *ctx.accounts.state_account.to_account_info().owner,
            crate::ID,
            DispatcherError::InvalidAccountOwner
        );

        // Security Validation: Verify vault authority matches expected PDA
        let (expected_authority, bump) = Pubkey::find_program_address(
            &[b"vault_authority", ctx.accounts.state_account.key().as_ref()],
            ctx.program_id,
        );
        require_keys_eq!(
            ctx.accounts.vault_authority.key(),
            expected_authority,
            DispatcherError::UnauthorizedVaultAuthority
        );

        // Perform CPI transfer with PDA signer seeds
        let state_key = ctx.accounts.state_account.key();
        let seeds = &[
            b"vault_authority".as_ref(),
            state_key.as_ref(),
            &[bump],
        ];
        let signer = &[&seeds[..]];

        let cpi_accounts = Transfer {
            from: ctx.accounts.vault_token_account.to_account_info(),
            to: ctx.accounts.recipient_token_account.to_account_info(),
            authority: ctx.accounts.vault_authority.to_account_info(),
        };
        let cpi_program = ctx.accounts.token_program.to_account_info();
        let cpi_ctx = CpiContext::new_with_signer(cpi_program, cpi_accounts, signer);

        token::transfer(cpi_ctx, amount)?;

        // Update state account internal balances securely
        let state = &mut ctx.accounts.state_account;
        state.total_dispatched = state
            .total_dispatched
            .checked_add(amount)
            .ok_or(DispatcherError::NumericalOverflow)?;

        emit!(LiquidityDispatchedEvent {
            recipient: ctx.accounts.recipient.key(),
            amount,
            timestamp: Clock::get()?.unix_timestamp,
        });

        Ok(())
    }
}

#[derive(Accounts)]
pub struct DispatchLiquidity<'info> {
    #[account(
        mut,
        has_one = authority @ DispatcherError::UnauthorizedAuthority,
        has_one = vault_token_account @ DispatcherError::InvalidVaultTokenAccount,
        owner = crate::ID @ DispatcherError::InvalidAccountOwner
    )]
    pub state_account: Account<'info, StateAccount>,

    /// CHECK: PDA derived and validated in instruction handler using seeds = [b"vault_authority", state_account.key().as_ref()]
    #[account(
        seeds = [b"vault_authority", state_account.key().as_ref()],
        bump
    )]
    pub vault_authority: AccountInfo<'info>,

    #[account(
        mut,
        constraint = vault_token_account.owner == vault_authority.key() @ DispatcherError::UnauthorizedVaultOwner
    )]
    pub vault_token_account: Account<'info, TokenAccount>,

    #[account(mut)]
    pub recipient_token_account: Account<'info, TokenAccount>,

    pub recipient: Signer<'info>,
    pub authority: Signer<'info>,
    pub token_program: Program<'info, Token>,
    pub system_program: Program<'info, System>,
}

#[account]
#[derive(Default)]
pub struct StateAccount {
    pub authority: Pubkey,
    pub vault_token_account: Pubkey,
    pub total_dispatched: u64,
    pub is_initialized: bool,
}

#[event]
pub struct LiquidityDispatchedEvent {
    pub recipient: Pubkey,
    pub amount: u64,
    pub timestamp: i64,
}

#[error_code]
pub enum DispatcherError {
    #[msg("Account owner does not match expected program ID")]
    InvalidAccountOwner,
    #[msg("Unauthorized authority for state account")]
    UnauthorizedAuthority,
    #[msg("Vault authority PDA does not match derived address")]
    UnauthorizedVaultAuthority,
    #[msg("Vault token account does not match registered state vault")]
    InvalidVaultTokenAccount,
    #[msg("Vault token account is not owned by vault authority PDA")]
    UnauthorizedVaultOwner,
    #[msg("Dispatch amount must be greater than zero")]
    ZeroAmount,
    #[msg("Numerical overflow during balance aggregation")]
    NumericalOverflow,
}
