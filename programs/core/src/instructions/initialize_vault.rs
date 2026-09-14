use anchor_lang::prelude::*;
use crate::state::VaultState;

/// Accounts required to initialize a new vault.
#[derive(Accounts)]
pub struct InitializeVault<'info> {
    #[account(
        init,
        payer = payer,
        space = 8 + VaultState::LEN,
    )]
    pub target_account: Account<'info, VaultState>,

    /// CHECK: Vault authority PDA derived from b"vault_authority".
    #[account(
        seeds = [b"vault_authority"],
        bump,
    )]
    pub vault_authority: AccountInfo<'info>,

    #[account(mut)]
    pub payer: Signer<'info>,

    pub system_program: Program<'info, System>,
}

/// Initializes vault state fields including PDA authority, bump seed, and liquidity.
pub fn init_vault(ctx: Context<InitializeVault>, total_liquidity: u64) -> Result<()> {
    let target = &mut ctx.accounts.target_account;
    target.vault_authority = ctx.accounts.vault_authority.key();
    target.authority_bump = ctx.bumps.vault_authority;
    target.total_liquidity = total_liquidity;
    Ok(())
}
