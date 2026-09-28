use anchor_lang::prelude::*;
use anchor_lang::solana_program::entrypoint::ProgramResult;

#[error_code]
pub enum ErrorCode {
    #[msg("Math overflow")]
    MathOverflow,
    // ... other error codes
}

pub fn checked_mul(a: u128, b: u128) -> Result<u128, ProgramError> {
    a.checked_mul(b).ok_or(ErrorCode::MathOverflow.into())
}

pub fn checked_div(a: u128, b: u128) -> Result<u128, ProgramError> {
    a.checked_div(b).ok_or(ErrorCode::MathOverflow.into())
}

pub fn checked_shl(a: u128, b: u32) -> Result<u128, ProgramError> {
    a.checked_shl(b).ok_or(ErrorCode::MathOverflow.into())
}

pub fn checked_shr(a: u128, b: u32) -> Result<u128, ProgramError> {
    a.checked_shr(b).ok_or(ErrorCode::MathOverflow.into())
}
