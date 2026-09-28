use anchor_lang::prelude::*;

/// Custom error set for the staking pool reward engine.
///
/// Every fallible arithmetic step returns one of these instead of relying on
/// a bare `unwrap()` / wrapping multiply, so an overflow can never silently
/// freeze withdrawals: it surfaces as a recoverable `ProgramError`.
#[error_code]
#[derive(Eq, PartialEq)]
pub enum PoolError {
    #[msg("Reward calculation overflowed u128 bounds")]
    RewardCalcOverflow,
    #[msg("Reward calculation division by zero")]
    RewardCalcDivByZero,
    #[msg("Reward calculation underflowed")]
    RewardCalcUnderflow,
    #[msg("Q64.64 fixed-point product overflowed")]
    RewardOverflow,
    #[msg("Q64.64 fixed-point quotient underflowed")]
    RewardUnderflow,
}
