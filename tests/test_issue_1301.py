"""Test suite for Anchor CPI account ownership and has_one constraint validation."""

import pytest

from packages.anchor_cpi_dispatcher import (
    AccountDiscriminatorMismatch,
    AccountInfo,
    AccountOwnerMismatch,
    AnchorCpiFormalVerifier,
    AnchorDispatcher,
    ConstraintHasOneMismatch,
    InsufficientLiquidityError,
    InvalidBumpError,
    NegativeAmountError,
    Pubkey,
    VaultState,
    VulnerableDispatcher,
)
from packages.anchor_cpi_dispatcher.dispatcher import DeserializationError


def test_successful_cpi_dispatch() -> None:
    """Tests successful liquidity dispatch when owner and has_one match."""
    program_id = Pubkey.from_seed(10)
    dispatcher = AnchorDispatcher(program_id)
    derived_pda, bump = Pubkey.find_program_address([b"vault_authority"], program_id)

    vault_state = VaultState(
        vault_authority=derived_pda,
        total_liquidity=50_000,
        authority_bump=bump,
    )

    auth_info = AccountInfo(
        key=derived_pda,
        owner=program_id,
        data=bytearray(),
        is_signer=True,
    )
    vault_info = AccountInfo(
        key=Pubkey.from_seed(20),
        owner=program_id,
        data=bytearray(vault_state.serialize()),
    )

    receipt = dispatcher.dispatch_cpi(auth_info, vault_info, 12_500)

    assert receipt.dispatched_amount == 12_500
    assert receipt.remaining_liquidity == 37_500
    assert receipt.target_vault == vault_info.key
    assert receipt.vault_authority == auth_info.key

    updated = dispatcher.fetch_vault_state(vault_info)
    assert updated.total_liquidity == 37_500


def test_counterfeit_account_owner_rejected() -> None:
    """Tests that an account owned by an external program is rejected."""
    program_id = Pubkey.from_seed(10)
    attacker_program = Pubkey.from_seed(99)
    dispatcher = AnchorDispatcher(program_id)
    derived_pda, bump = Pubkey.find_program_address([b"vault_authority"], program_id)

    counterfeit_state = VaultState(
        vault_authority=derived_pda,
        total_liquidity=1_000_000,
        authority_bump=bump,
    )

    auth_info = AccountInfo(key=derived_pda, owner=program_id, data=bytearray())
    counterfeit_info = AccountInfo(
        key=Pubkey.from_seed(55),
        owner=attacker_program,
        data=bytearray(counterfeit_state.serialize()),
    )

    with pytest.raises(AccountOwnerMismatch) as exc_info:
        dispatcher.dispatch_cpi(auth_info, counterfeit_info, 500_000)

    assert "does not match expected" in str(exc_info.value)


def test_account_discriminator_mismatch_rejected() -> None:
    """Tests that an account with invalid discriminator bytes is rejected."""
    program_id = Pubkey.from_seed(10)
    dispatcher = AnchorDispatcher(program_id)
    derived_pda, bump = Pubkey.find_program_address([b"vault_authority"], program_id)

    vault_state = VaultState(
        vault_authority=derived_pda,
        total_liquidity=10_000,
        authority_bump=bump,
    )

    corrupted_data = bytearray(vault_state.serialize())
    corrupted_data[:8] = b"INVALID!"

    auth_info = AccountInfo(key=derived_pda, owner=program_id, data=bytearray())
    corrupt_info = AccountInfo(
        key=Pubkey.from_seed(33),
        owner=program_id,
        data=corrupted_data,
    )

    with pytest.raises(AccountDiscriminatorMismatch):
        dispatcher.dispatch_cpi(auth_info, corrupt_info, 1_000)


def test_truncated_account_buffer_rejected() -> None:
    """Tests that a buffer smaller than the minimum state length is rejected."""
    program_id = Pubkey.from_seed(10)
    dispatcher = AnchorDispatcher(program_id)
    derived_pda, _ = Pubkey.find_program_address([b"vault_authority"], program_id)

    auth_info = AccountInfo(key=derived_pda, owner=program_id, data=bytearray())
    truncated_info = AccountInfo(
        key=Pubkey.from_seed(34),
        owner=program_id,
        data=bytearray(b"tooshort"),
    )

    with pytest.raises(DeserializationError):
        dispatcher.dispatch_cpi(auth_info, truncated_info, 1_000)


def test_unauthorized_vault_authority_has_one_violated() -> None:
    """Tests that has_one constraint prevents mismatched authority accounts."""
    program_id = Pubkey.from_seed(10)
    dispatcher = AnchorDispatcher(program_id)
    derived_pda, bump = Pubkey.find_program_address([b"vault_authority"], program_id)
    unauthorized_authority = Pubkey.from_seed(77)

    forged_state = VaultState(
        vault_authority=unauthorized_authority,
        total_liquidity=20_000,
        authority_bump=bump,
    )

    auth_info = AccountInfo(key=derived_pda, owner=program_id, data=bytearray())
    vault_info = AccountInfo(
        key=Pubkey.from_seed(88),
        owner=program_id,
        data=bytearray(forged_state.serialize()),
    )

    with pytest.raises(ConstraintHasOneMismatch) as exc_info:
        dispatcher.dispatch_cpi(auth_info, vault_info, 5_000)

    assert "Constraint has_one violated" in str(exc_info.value)


def test_invalid_authority_pda_mismatch() -> None:
    """Tests that an arbitrary public key supplied as authority PDA is rejected."""
    program_id = Pubkey.from_seed(10)
    dispatcher = AnchorDispatcher(program_id)
    _, bump = Pubkey.find_program_address([b"vault_authority"], program_id)
    counterfeit_pda = Pubkey.from_seed(99)

    vault_state = VaultState(
        vault_authority=counterfeit_pda,
        total_liquidity=15_000,
        authority_bump=bump,
    )

    auth_info = AccountInfo(key=counterfeit_pda, owner=program_id, data=bytearray())
    vault_info = AccountInfo(
        key=Pubkey.from_seed(66),
        owner=program_id,
        data=bytearray(vault_state.serialize()),
    )

    with pytest.raises(ConstraintHasOneMismatch) as exc_info:
        dispatcher.dispatch_cpi(auth_info, vault_info, 2_000)

    assert "Vault authority PDA mismatch" in str(exc_info.value)


def test_authority_bump_mismatch_rejected() -> None:
    """Tests that a tampered authority bump seed is detected and rejected."""
    program_id = Pubkey.from_seed(10)
    dispatcher = AnchorDispatcher(program_id)
    derived_pda, _ = Pubkey.find_program_address([b"vault_authority"], program_id)

    vault_state = VaultState(
        vault_authority=derived_pda,
        total_liquidity=15_000,
        authority_bump=123,
    )

    auth_info = AccountInfo(key=derived_pda, owner=program_id, data=bytearray())
    vault_info = AccountInfo(
        key=Pubkey.from_seed(67),
        owner=program_id,
        data=bytearray(vault_state.serialize()),
    )

    with pytest.raises(InvalidBumpError) as exc_info:
        dispatcher.dispatch_cpi(auth_info, vault_info, 2_000)

    assert "Authority bump mismatch" in str(exc_info.value)


def test_insufficient_liquidity_rejection() -> None:
    """Tests that dispatch exceeding balance is rejected without mutating state."""
    program_id = Pubkey.from_seed(10)
    dispatcher = AnchorDispatcher(program_id)
    derived_pda, bump = Pubkey.find_program_address([b"vault_authority"], program_id)

    vault_state = VaultState(
        vault_authority=derived_pda,
        total_liquidity=5_000,
        authority_bump=bump,
    )

    auth_info = AccountInfo(key=derived_pda, owner=program_id, data=bytearray())
    vault_info = AccountInfo(
        key=Pubkey.from_seed(22),
        owner=program_id,
        data=bytearray(vault_state.serialize()),
    )

    with pytest.raises(InsufficientLiquidityError):
        dispatcher.dispatch_cpi(auth_info, vault_info, 10_000)

    unchanged = dispatcher.fetch_vault_state(vault_info)
    assert unchanged.total_liquidity == 5_000


def test_negative_or_zero_amount_rejected() -> None:
    """Tests that zero and negative amounts are rejected."""
    program_id = Pubkey.from_seed(10)
    dispatcher = AnchorDispatcher(program_id)
    derived_pda, bump = Pubkey.find_program_address([b"vault_authority"], program_id)

    vault_state = VaultState(
        vault_authority=derived_pda,
        total_liquidity=5_000,
        authority_bump=bump,
    )

    auth_info = AccountInfo(key=derived_pda, owner=program_id, data=bytearray())
    vault_info = AccountInfo(
        key=Pubkey.from_seed(23),
        owner=program_id,
        data=bytearray(vault_state.serialize()),
    )

    with pytest.raises(NegativeAmountError):
        dispatcher.dispatch_cpi(auth_info, vault_info, 0)

    with pytest.raises(NegativeAmountError):
        dispatcher.dispatch_cpi(auth_info, vault_info, -500)


def test_vulnerable_dispatcher_permits_counterfeit_state() -> None:
    """Tests that vulnerable dispatcher fails to detect counterfeit accounts."""
    program_id = Pubkey.from_seed(10)
    counterfeit_owner = Pubkey.from_seed(77)
    vulnerable = VulnerableDispatcher(program_id)
    derived_pda, bump = Pubkey.find_program_address([b"vault_authority"], program_id)

    vault_state = VaultState(
        vault_authority=derived_pda,
        total_liquidity=100_000,
        authority_bump=bump,
    )

    auth_info = AccountInfo(key=derived_pda, owner=program_id, data=bytearray())
    counterfeit_vault = AccountInfo(
        key=Pubkey.from_seed(99),
        owner=counterfeit_owner,
        data=bytearray(vault_state.serialize()),
    )

    receipt = vulnerable.dispatch_cpi(auth_info, counterfeit_vault, 50_000)
    assert receipt.dispatched_amount == 50_000
    assert receipt.remaining_liquidity == 50_000


def test_pubkey_properties_and_base58() -> None:
    """Tests Pubkey construction, validation, and Base58 representation."""
    valid_key = Pubkey.from_seed(5)
    assert len(valid_key.data) == 32
    assert len(valid_key.to_base58()) > 0
    assert str(valid_key) == valid_key.to_base58()

    with pytest.raises(ValueError):
        Pubkey(b"short_bytes")


def test_formal_invariant_verification_suite() -> None:
    """Tests that all formal mathematical invariant proofs pass successfully."""
    verifier = AnchorCpiFormalVerifier()
    proofs = verifier.run_all_proofs()

    assert len(proofs) == 7
    for proof in proofs:
        assert proof.verified is True
        assert len(proof.details) > 0
