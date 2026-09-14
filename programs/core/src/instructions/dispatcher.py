"""Secure Anchor CPI dispatcher.

Fixes the missing account ownership validation in the Anchor CPI
dispatcher.  Caller-supplied accounts are deserialized only through a
typed ``Account<'info, T>`` wrapper that verifies
``AccountInfo.owner == expected_program_id``, and the Anchor ``has_one``
constraint on the vault authority PDA is strictly enforced before any
synthetic liquidity can be minted.
"""

from __future__ import annotations

from dataclasses import dataclass
from struct import pack, unpack_from
from typing import Generic, Type, TypeVar

MAX_PUBKEY_LEN = 32
VAULT_LAYOUT = "<32sBQ"


class ProgramError(Exception):
    """Base class for Anchor-style program errors."""

    code = 0

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AccountOwnerMismatch(ProgramError):
    """Raised when an account is owned by an unexpected program."""

    code = 13


class MissingRequiredSignature(ProgramError):
    """Raised when a required signer is missing."""

    code = 101


class ConstraintHasOne(ProgramError):
    """Raised when a has_one constraint is violated."""

    code = 2002


@dataclass(frozen=True)
class Pubkey:
    """A 32-byte Solana public key."""

    data: bytes

    def __post_init__(self) -> None:
        if len(self.data) != MAX_PUBKEY_LEN:
            raise ValueError("pubkey must be exactly 32 bytes")

    def __str__(self) -> str:
        return self.data.hex()


@dataclass
class AccountInfo:
    """Raw account metadata supplied by the instruction caller."""

    key: Pubkey
    owner: Pubkey
    data: bytes
    is_signer: bool = False
    is_writable: bool = False
    lamports: int = 0


class AnchorModel:
    """Base class for on-chain account layouts."""

    @classmethod
    def deserialize(cls, raw: bytes) -> "AnchorModel":
        """Deserialize ``raw`` bytes into a model instance."""
        raise NotImplementedError

    def serialize(self) -> bytes:
        """Serialize this model back to its on-chain byte layout."""
        raise NotImplementedError


ModelT = TypeVar("ModelT", bound=AnchorModel)


@dataclass
class Account(Generic[ModelT]):
    """Typed Anchor ``Account<'info, T>`` wrapper.

    Deserialization only succeeds when ``info.owner == program_id``.
    Otherwise :class:`AccountOwnerMismatch` is raised before any CPI can
    be invoked with the caller-supplied data.
    """

    info: AccountInfo
    program_id: Pubkey
    value: ModelT

    @classmethod
    def load(
        cls,
        info: AccountInfo,
        program_id: Pubkey,
        model: Type[ModelT],
    ) -> "Account[ModelT]":
        if info.owner != program_id:
            raise AccountOwnerMismatch(
                f"account {info.key} is owned by {info.owner}, expected {program_id}"
            )
        value = model.deserialize(info.data)
        return cls(info=info, program_id=program_id, value=value)


@dataclass
class Vault(AnchorModel):
    """Vault state account layout.

    Field order matches the on-chain layout consumed by the typed
    ``Account<'info, Vault>`` wrapper: authority (32 bytes), bump
    (1 byte) and minted supply (u64, 8 bytes).
    """

    authority: Pubkey
    bump: int
    minted: int

    @classmethod
    def deserialize(cls, raw: bytes) -> "Vault":
        if len(raw) < 41:
            raise ProgramError("account data too short")
        authority, bump, minted = unpack_from(VAULT_LAYOUT, raw, 0)
        return cls(authority=Pubkey(authority), bump=bump, minted=minted)

    def serialize(self) -> bytes:
        return pack(VAULT_LAYOUT, self.authority.data, self.bump, self.minted)


@dataclass(frozen=True)
class MintReceipt:
    """Outcome of a successfully validated mint dispatch."""

    vault: Pubkey
    authority: Pubkey
    minted: int
    total_supply: int


class Dispatcher:
    """CPI dispatcher enforcing ownership and ``has_one`` constraints."""

    def __init__(self, program_id: Pubkey) -> None:
        self.program_id = program_id

    def mint(
        self,
        vault_info: AccountInfo,
        vault_authority_info: AccountInfo,
        amount: int,
    ) -> MintReceipt:
        vault_account = Account.load(vault_info, self.program_id, Vault)
        if vault_account.value.authority != vault_authority_info.key:
            raise ConstraintHasOne(
                f"vault authority {vault_authority_info.key} does not match "
                f"vault.authority {vault_account.value.authority}"
            )
        if not vault_authority_info.is_signer:
            raise MissingRequiredSignature("vault authority must sign the CPI")
        if amount <= 0:
            raise ProgramError("amount must be positive")
        total_supply = vault_account.value.minted + amount
        vault_account.value.minted = total_supply
        vault_info.data = vault_account.value.serialize()
        return MintReceipt(
            vault=vault_info.key,
            authority=vault_authority_info.key,
            minted=amount,
            total_supply=total_supply,
        )


__all__ = [
    "Account",
    "AccountInfo",
    "AccountOwnerMismatch",
    "AnchorModel",
    "ConstraintHasOne",
    "Dispatcher",
    "MintReceipt",
    "MissingRequiredSignature",
    "ProgramError",
    "Pubkey",
    "Vault",
]