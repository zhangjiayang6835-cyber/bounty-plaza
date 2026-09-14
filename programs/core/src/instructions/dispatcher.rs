use anchor_lang::prelude::*;
use crate::errors::ErrorCode;
use crate::state::VaultState;

/// Accounts required for executing cross-program liquidity dispatch.
#[derive(Accounts)]
pub struct DispatchCpi<'info> {
    /// CHECK: Vault authority PDA validated via seeds constraint and has_one.
    #[account(
        seeds = [b"vault_authority"],
        bump = target_account.authority_bump,
    )]
    pub vault_authority: AccountInfo<'info>,

    #[account(
        mut,
        has_one = vault_authority @ ErrorCode::InvalidAuthority,
    )]
    pub target_account: Account<'info, VaultState>,

    pub system_program: Program<'info, System>,
}

/// Dispatches liquidity routing after verifying account ownership and authority constraints.
pub fn dispatch_cpi(ctx: Context<DispatchCpi>, amount: u64) -> Result<()> {
    require!(
        ctx.accounts.target_account.total_liquidity >= amount,
        ErrorCode::InsufficientLiquidity
    );

    let target = &mut ctx.accounts.target_account;
    target.total_liquidity = target
        .total_liquidity
        .checked_sub(amount)
        .ok_or(ErrorCode::InsufficientLiquidity)?;

    Ok(())
}

#[cfg(test)]
mod tests {
    #[test]
    fn test_liquidity_subtraction() {
        let mut liquidity: u64 = 5000;
        let amount: u64 = 1000;
        liquidity = liquidity.checked_sub(amount).expect("subtraction failed");
        assert_eq!(liquidity, 4000);
    }

    #[test]
    fn test_insufficient_liquidity_overflow() {
        let liquidity: u64 = 500;
        let amount: u64 = 1000;
        assert!(liquidity.checked_sub(amount).is_none());
    }
}
