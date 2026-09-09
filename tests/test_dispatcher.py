"""Integration tests for the hardened Anchor CPI dispatcher.

Verifies that caller-supplied accounts are only deserialized through the
typed ``Account<'info, T>`` wrapper (owner check) and that the ``has_one``
vault authority constraint is enforced before any synthetic liquidity can
be minted.
"""

from struct import pack

import pytest

from programs.core.src.instructions.dispatcher import (
    Account,
    AccountInfo,
    AccountOwnerMismatch,
    ConstraintHasOne,
    Dispatcher,
    MintReceipt,
    MissingRequiredSignature,
    ProgramError,
    Pubkey,
    Vault,
)


def _key(seed: int) -> Pubkey:
    return Pubkey(bytes([seed]) * 32)


def _vault_data(authority: Pubkey, bump: int = 255, minted: int = 0) -> bytes:
    return pack("<32sBQ", authority.data, bump, minted)


@pytest.fixture
def program_id() -> Pubkey:
    return _key(1)


@pytest.fixture
def authority() -> Pubkey:
    return _key(2)


@pytest.fixture
def vault_info(program_id: Pubkey, authority: Pubkey) -> AccountInfo:
    return AccountInfo(
        key=_key(3),
        owner=program_id,
        data=_vault_data(authority),
        is_writable=True,
    )


@pytest.fixture
def authority_info(authority: Pubkey) -> AccountInfo:
    return AccountInfo(key=authority, owner=_key(1), data=b"", is_signer=True)


def test_accepts_vault_owned_by_program(
    program_id: Pubkey,
    vault_info: AccountInfo,
    authority_info: AccountInfo,
) -> None:
    receipt = Dispatcher(program_id).mint(vault_info, authority_info, amount=100)
    assert isinstance(receipt, MintReceipt)
    assert receipt.minted == 100
    assert receipt.total_supply == 100


def test_typed_account_wrapper_checks_owner(
    program_id: Pubkey,
    vault_info: AccountInfo,
    authority: Pubkey,
) -> None:
    account = Account.load(vault_info, program_id, Vault)
    assert account.value.authority == authority
    assert account.value.minted == 0


def test_rejects_counterfeit_vault_with_wrong_owner(
    program_id: Pubkey,
    authority_info: AccountInfo,
) -> None:
    counterfeit = AccountInfo(
        key=_key(9),
        owner=_key(42),
        data=_vault_data(authority_info.key),
        is_writable=True,
    )
    with pytest.raises(AccountOwnerMismatch):
        Dispatcher(program_id).mint(counterfeit, authority_info, amount=1_000_000)


def test_rejects_has_one_authority_mismatch(
    program_id: Pubkey,
    vault_info: AccountInfo,
) -> None:
    attacker = AccountInfo(key=_key(7), owner=_key(1), data=b"", is_signer=True)
    with pytest.raises(ConstraintHasOne):
        Dispatcher(program_id).mint(vault_info, attacker, amount=1_000_000)


def test_requires_authority_signer(
    program_id: Pubkey,
    vault_info: AccountInfo,
    authority: Pubkey,
) -> None:
    unsigned = AccountInfo(key=authority, owner=_key(1), data=b"", is_signer=False)
    with pytest.raises(MissingRequiredSignature):
        Dispatcher(program_id).mint(vault_info, unsigned, amount=1)


def test_rejects_non_positive_amount(
    program_id: Pubkey,
    vault_info: AccountInfo,
    authority_info: AccountInfo,
) -> None:
    with pytest.raises(ProgramError):
        Dispatcher(program_id).mint(vault_info, authority_info, amount=0)


def test_rejects_truncated_account_data(
    program_id: Pubkey,
) -> None:
    truncated = AccountInfo(
        key=_key(3),
        owner=program_id,
        data=b"\x00" * 4,
    )
    with pytest.raises(ProgramError):
        Account.load(truncated, program_id, Vault)


def test_mint_accumulates_total_supply(
    program_id: Pubkey,
    vault_info: AccountInfo,
    authority_info: AccountInfo,
) -> None:
    dispatcher = Dispatcher(program_id)
    first = dispatcher.mint(vault_info, authority_info, amount=50)
    second = dispatcher.mint(vault_info, authority_info, amount=25)
    assert first.total_supply == 50
    assert second.total_supply == 75