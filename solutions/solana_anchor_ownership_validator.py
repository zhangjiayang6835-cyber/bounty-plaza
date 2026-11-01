"""
Solana Anchor Account Ownership & CPI Dispatcher Security Engine.
Validates CWE-284, CWE-285, and Anchor macro constraints to prevent
counterfeit state account injection attacks.
"""

from dataclasses import dataclass
from typing import Tuple, Dict, Any
import hashlib


PROGRAM_ID = "Disp1atcher11111111111111111111111111111111"
SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"


class DispatcherSecurityError(Exception):
    """Raised when an Anchor security invariant is violated."""


@dataclass
class MockAccountInfo:
    """Mock representation of Solana AccountInfo for testing invariants."""
    pubkey: str
    owner: str
    lamports: int
    data: bytes
    is_signer: bool
    is_writable: bool


@dataclass
class StateAccountData:
    """Mock deserialized StateAccount struct data."""
    authority: str
    vault_token_account: str
    total_dispatched: int
    is_initialized: bool


@dataclass
class DispatchContext:
    """Context wrapper containing all accounts required for dispatch."""
    state_account: MockAccountInfo
    state_data: StateAccountData
    vault_authority: MockAccountInfo
    vault_token_account: MockAccountInfo
    caller_authority: MockAccountInfo
    amount: int


def derive_vault_pda(state_pubkey: str, program_id: str = PROGRAM_ID) -> Tuple[str, int]:
    """Derives deterministic PDA address and bump for vault authority."""
    seed_data = b"vault_authority" + state_pubkey.encode("utf-8") + program_id.encode("utf-8")
    derived_hash = hashlib.sha256(seed_data).hexdigest()
    derived_pubkey = f"pda_{derived_hash[:32]}"
    bump = 254
    return derived_pubkey, bump


class AnchorDispatcherGuard:
    """
    Enforces strict Anchor runtime checks:
    1. Account owner verification against program ID.
    2. has_one constraint verification on state authority and vault.
    3. PDA seed integrity check.
    4. Signer authorization.
    """

    def __init__(self, program_id: str = PROGRAM_ID):
        self.program_id = program_id

    def verify_account_owner(self, account: MockAccountInfo) -> bool:
        """Explicitly checks whether the account is owned by the expected program."""
        if account.owner != self.program_id:
            raise DispatcherSecurityError(
                f"InvalidAccountOwner: Expected owner {self.program_id}, got {account.owner}"
            )
        return True

    def validate_and_dispatch(self, ctx: DispatchContext) -> Dict[str, Any]:
        """Simulates Anchor CPI execution with rigorous constraint validation."""
        if ctx.amount <= 0:
            raise DispatcherSecurityError("ZeroAmount: Dispatch amount must be greater than zero")

        # Security Validation: Account Ownership Check (Mitigates Issue #1301)
        self.verify_account_owner(ctx.state_account)

        # Security Validation: has_one = authority check
        if ctx.state_data.authority != ctx.caller_authority.pubkey:
            raise DispatcherSecurityError(
                f"UnauthorizedAuthority: Expected authority {ctx.state_data.authority}, "
                f"got {ctx.caller_authority.pubkey}"
            )

        if not ctx.caller_authority.is_signer:
            raise DispatcherSecurityError("SignerRequired: Caller authority must sign transaction")

        # Security Validation: has_one = vault_token_account check
        if ctx.state_data.vault_token_account != ctx.vault_token_account.pubkey:
            raise DispatcherSecurityError(
                "InvalidVaultTokenAccount: Vault mismatch with state account"
            )

        # Security Validation: PDA Seed & Authority Check
        expected_pda, _ = derive_vault_pda(ctx.state_account.pubkey, self.program_id)
        if ctx.vault_authority.pubkey != expected_pda:
            raise DispatcherSecurityError(
                f"UnauthorizedVaultAuthority: Vault authority {ctx.vault_authority.pubkey} "
                f"does not match PDA {expected_pda}"
            )

        # Security Validation: Vault Token Account Owner Check
        if ctx.vault_token_account.owner != ctx.vault_authority.pubkey:
            raise DispatcherSecurityError(
                "UnauthorizedVaultOwner: Vault token account is not owned by vault PDA"
            )

        # All invariants passed
        new_total = ctx.state_data.total_dispatched + ctx.amount
        ctx.state_data.total_dispatched = new_total

        return {
            "status": "SUCCESS",
            "dispatched_amount": ctx.amount,
            "new_total": new_total,
            "vault_pda": expected_pda,
            "recipient_credited": True,
        }
