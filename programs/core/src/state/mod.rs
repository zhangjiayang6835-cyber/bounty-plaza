use anchor_lang::prelude::*;

pub mod pool;
pub use pool::*;

/// State account representing a liquidity vault.
#[account]
pub struct VaultState {
    pub vault_authority: Pubkey,
    pub total_liquidity: u64,
    pub authority_bump: u8,
}

impl VaultState {
    pub const LEN: usize = 32 + 8 + 1;
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_vault_state_len() {
        assert_eq!(VaultState::LEN, 41);
    }
}
