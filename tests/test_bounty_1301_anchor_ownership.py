"""
Test Suite for Bounty #1301: Missing Account Ownership Validation in Anchor CPI Dispatcher.
Validates:
- Rejection of counterfeit state account with attacker-controlled program owner.
- Enforcement of has_one = authority and has_one = vault_token_account.
- Rejection of mismatched or spoofed PDA vault authority.
- Successful dispatch when all Anchor ownership constraints are fulfilled.
"""

import os
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest
from solutions.solana_anchor_ownership_validator import (
    AnchorDispatcherGuard,
    MockAccountInfo,
    StateAccountData,
    DispatchContext,
    DispatcherSecurityError,
    derive_vault_pda,
    PROGRAM_ID,
)


@pytest.fixture
def guard():
    return AnchorDispatcherGuard(program_id=PROGRAM_ID)


@pytest.fixture
def valid_state_setup():
    state_pubkey = "state_legit_account_111111111111111111111"
    authority_pubkey = "auth_genuine_pubkey_22222222222222222222"
    vault_token_pubkey = "vault_token_account_3333333333333333333"

    pda_pubkey, bump = derive_vault_pda(state_pubkey, PROGRAM_ID)

    state_acc = MockAccountInfo(
        pubkey=state_pubkey,
        owner=PROGRAM_ID,  # Genuine program ownership
        lamports=10_000_000,
        data=b"serialized_state",
        is_signer=False,
        is_writable=True,
    )

    state_data = StateAccountData(
        authority=authority_pubkey,
        vault_token_account=vault_token_pubkey,
        total_dispatched=500_000,
        is_initialized=True,
    )

    vault_authority_acc = MockAccountInfo(
        pubkey=pda_pubkey,
        owner=PROGRAM_ID,
        lamports=1_000_000,
        data=b"",
        is_signer=False,
        is_writable=False,
    )

    vault_token_acc = MockAccountInfo(
        pubkey=vault_token_pubkey,
        owner=pda_pubkey,  # Owned by vault PDA
        lamports=5_000_000,
        data=b"",
        is_signer=False,
        is_writable=True,
    )

    caller_auth_acc = MockAccountInfo(
        pubkey=authority_pubkey,
        owner="11111111111111111111111111111111",
        lamports=1_000_000,
        data=b"",
        is_signer=True,
        is_writable=False,
    )

    return {
        "state_acc": state_acc,
        "state_data": state_data,
        "vault_authority_acc": vault_authority_acc,
        "vault_token_acc": vault_token_acc,
        "caller_auth_acc": caller_auth_acc,
    }


def test_bounty_1301_counterfeit_state_account_rejected(guard, valid_state_setup):
    """
    CRITICAL EXPLOIT MITIGATION TEST:
    An attacker crafts a state account owned by a malicious third-party program
    in order to bypass authority checks and drain synthetic liquidity.
    Must be blocked with InvalidAccountOwner.
    """
    s = valid_state_setup
    counterfeit_state = MockAccountInfo(
        pubkey="attacker_fake_state_99999999999999999999",
        owner="AttackerProgram11111111111111111111111111111",  # Malicious owner!
        lamports=1_000,
        data=b"fake_state_data",
        is_signer=False,
        is_writable=True,
    )

    ctx = DispatchContext(
        state_account=counterfeit_state,
        state_data=s["state_data"],
        vault_authority=s["vault_authority_acc"],
        vault_token_account=s["vault_token_acc"],
        caller_authority=s["caller_auth_acc"],
        amount=100_000,
    )

    with pytest.raises(DispatcherSecurityError, match="InvalidAccountOwner"):
        guard.validate_and_dispatch(ctx)


def test_unauthorized_authority_rejected(guard, valid_state_setup):
    """Verifies has_one = authority rejects unauthorized signer."""
    s = valid_state_setup
    attacker_auth = MockAccountInfo(
        pubkey="unauthorized_attacker_key_88888888888888888",
        owner="11111111111111111111111111111111",
        lamports=1_000,
        data=b"",
        is_signer=True,
        is_writable=False,
    )

    ctx = DispatchContext(
        state_account=s["state_acc"],
        state_data=s["state_data"],
        vault_authority=s["vault_authority_acc"],
        vault_token_account=s["vault_token_acc"],
        caller_authority=attacker_auth,
        amount=100_000,
    )

    with pytest.raises(DispatcherSecurityError, match="UnauthorizedAuthority"):
        guard.validate_and_dispatch(ctx)


def test_unauthorized_vault_authority_pda_rejected(guard, valid_state_setup):
    """Verifies that an arbitrary or spoofed vault authority PDA is rejected."""
    s = valid_state_setup
    spoofed_pda = MockAccountInfo(
        pubkey="spoofed_pda_pubkey_77777777777777777777",
        owner=PROGRAM_ID,
        lamports=100,
        data=b"",
        is_signer=False,
        is_writable=False,
    )

    ctx = DispatchContext(
        state_account=s["state_acc"],
        state_data=s["state_data"],
        vault_authority=spoofed_pda,
        vault_token_account=s["vault_token_acc"],
        caller_authority=s["caller_auth_acc"],
        amount=100_000,
    )

    with pytest.raises(DispatcherSecurityError, match="UnauthorizedVaultAuthority"):
        guard.validate_and_dispatch(ctx)


def test_zero_amount_rejected(guard, valid_state_setup):
    """Verifies zero amount input is rejected."""
    s = valid_state_setup
    ctx = DispatchContext(
        state_account=s["state_acc"],
        state_data=s["state_data"],
        vault_authority=s["vault_authority_acc"],
        vault_token_account=s["vault_token_acc"],
        caller_authority=s["caller_auth_acc"],
        amount=0,
    )

    with pytest.raises(DispatcherSecurityError, match="ZeroAmount"):
        guard.validate_and_dispatch(ctx)


def test_valid_dispatch_success(guard, valid_state_setup):
    """Verifies that legitimate invocations succeed and aggregate balances properly."""
    s = valid_state_setup
    ctx = DispatchContext(
        state_account=s["state_acc"],
        state_data=s["state_data"],
        vault_authority=s["vault_authority_acc"],
        vault_token_account=s["vault_token_acc"],
        caller_authority=s["caller_auth_acc"],
        amount=100_000,
    )

    result = guard.validate_and_dispatch(ctx)

    assert result["status"] == "SUCCESS"
    assert result["dispatched_amount"] == 100_000
    assert result["new_total"] == 600_000
    assert result["recipient_credited"] is True
