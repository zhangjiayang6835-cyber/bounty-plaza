"""Pytest test suite validating SafeERC20 asset transfer hooks and batch harvesting for Issue #1302."""

import pytest
from packages.safe_transfer_vault import (
    BatchYieldHarvesterModel,
    SafeERC20Wrapper,
    SafeTransferError,
    SafeTransferFormalVerifier,
    TokenModel,
    TokenType,
    VulnerableYieldHarvesterModel,
)


def test_standard_token_transfer_success():
    """Validates that standard ERC-20 transfers succeed and update balances."""
    token = TokenModel(
        name="Standard USD",
        symbol="SUSD",
        decimals=18,
        token_type=TokenType.STANDARD,
    )
    token.mint("0xHarvester", 10_000)

    harvester = BatchYieldHarvesterModel("0xHarvester")
    harvester.harvest_yield(token, "0xAlice", 3_000)

    assert token.balance_of("0xAlice") == 3_000
    assert token.balance_of("0xHarvester") == 7_000


def test_usdt_no_return_transfer_success():
    """Validates that non-standard USDT (void return) succeeds with SafeERC20 wrapper."""
    token = TokenModel(
        name="Tether USD",
        symbol="USDT",
        decimals=6,
        token_type=TokenType.NO_RETURN,
    )
    token.mint("0xHarvester", 10_000)

    harvester = BatchYieldHarvesterModel("0xHarvester")
    harvester.harvest_yield(token, "0xBob", 4_500)

    assert token.balance_of("0xBob") == 4_500
    assert token.balance_of("0xHarvester") == 5_500


def test_batch_harvest_mixed_tokens():
    """Validates that batch harvesting succeeds across mixed standard and non-standard tokens."""
    token_std = TokenModel(
        name="Standard USD",
        symbol="SUSD",
        decimals=18,
        token_type=TokenType.STANDARD,
    )
    token_usdt = TokenModel(
        name="Tether USD",
        symbol="USDT",
        decimals=6,
        token_type=TokenType.NO_RETURN,
    )
    token_std.mint("0xHarvester", 10_000)
    token_usdt.mint("0xHarvester", 20_000)

    harvester = BatchYieldHarvesterModel("0xHarvester")
    tokens = [token_std, token_usdt]
    recipients = ["0xAlice", "0xBob"]
    amounts = [2_500, 7_500]

    count = harvester.batch_harvest_yield(tokens, recipients, amounts)

    assert count == 2
    assert token_std.balance_of("0xAlice") == 2_500
    assert token_usdt.balance_of("0xBob") == 7_500


def test_vulnerable_harvester_reverts_on_usdt():
    """Validates that direct transfer call fails on non-standard USDT token."""
    token = TokenModel(
        name="Tether USD",
        symbol="USDT",
        decimals=6,
        token_type=TokenType.NO_RETURN,
    )
    token.mint("0xVulnerable", 10_000)

    vulnerable = VulnerableYieldHarvesterModel("0xVulnerable")
    with pytest.raises(SafeTransferError, match="ABI decoding error"):
        vulnerable.harvest_yield_direct(token, "0xAlice", 1_000)


def test_vulnerable_batch_harvest_reverts_on_usdt():
    """Validates that vulnerable batch harvester fails when one token is USDT."""
    token_std = TokenModel(
        name="Standard USD",
        symbol="SUSD",
        decimals=18,
        token_type=TokenType.STANDARD,
    )
    token_usdt = TokenModel(
        name="Tether USD",
        symbol="USDT",
        decimals=6,
        token_type=TokenType.NO_RETURN,
    )
    token_std.mint("0xVulnerable", 10_000)
    token_usdt.mint("0xVulnerable", 10_000)

    vulnerable = VulnerableYieldHarvesterModel("0xVulnerable")
    tokens = [token_std, token_usdt]
    recipients = ["0xAlice", "0xBob"]
    amounts = [1_000, 1_000]

    with pytest.raises(SafeTransferError, match="ABI decoding error"):
        vulnerable.batch_harvest_yield_direct(tokens, recipients, amounts)


def test_false_return_token_reverts():
    """Validates that false-returning tokens are rejected by SafeERC20."""
    token = TokenModel(
        name="False USD",
        symbol="FUSD",
        decimals=18,
        token_type=TokenType.FALSE_RETURN,
        should_fail=True,
    )
    token.mint("0xHarvester", 5_000)

    harvester = BatchYieldHarvesterModel("0xHarvester")
    with pytest.raises(SafeTransferError, match="SafeERC20FailedOperation"):
        harvester.harvest_yield(token, "0xAlice", 1_000)


def test_reverting_token_raises_error():
    """Validates that tokens that revert on transfer raise SafeTransferError."""
    token = TokenModel(
        name="Revert USD",
        symbol="RUSD",
        decimals=18,
        token_type=TokenType.REVERTING,
    )
    token.mint("0xHarvester", 5_000)

    harvester = BatchYieldHarvesterModel("0xHarvester")
    with pytest.raises(SafeTransferError, match="transfer reverted"):
        harvester.harvest_yield(token, "0xAlice", 1_000)


def test_deposit_asset_standard_and_non_standard():
    """Validates depositAsset via safeTransferFrom for standard and non-standard tokens."""
    token_std = TokenModel(
        name="Standard USD",
        symbol="SUSD",
        decimals=18,
        token_type=TokenType.STANDARD,
    )
    token_usdt = TokenModel(
        name="Tether USD",
        symbol="USDT",
        decimals=6,
        token_type=TokenType.NO_RETURN,
    )
    token_std.mint("0xUser", 5_000)
    token_usdt.mint("0xUser", 5_000)

    token_std.approve("0xUser", "0xHarvester", 5_000)
    token_usdt.approve("0xUser", "0xHarvester", 5_000)

    harvester = BatchYieldHarvesterModel("0xHarvester")
    harvester.deposit_asset(token_std, "0xUser", 2_000)
    harvester.deposit_asset(token_usdt, "0xUser", 3_000)

    assert token_std.balance_of("0xHarvester") == 2_000
    assert token_usdt.balance_of("0xHarvester") == 3_000
    assert token_std.balance_of("0xUser") == 3_000
    assert token_usdt.balance_of("0xUser") == 2_000


def test_withdraw_asset():
    """Validates withdrawAsset using SafeERC20."""
    token = TokenModel(
        name="Tether USD",
        symbol="USDT",
        decimals=6,
        token_type=TokenType.NO_RETURN,
    )
    token.mint("0xHarvester", 8_000)

    harvester = BatchYieldHarvesterModel("0xHarvester")
    harvester.withdraw_asset(token, "0xTreasury", 3_500)

    assert token.balance_of("0xTreasury") == 3_500
    assert token.balance_of("0xHarvester") == 4_500


def test_force_approve_handles_usdt_reset():
    """Validates that force approve resets allowance when required by USDT."""
    token = TokenModel(
        name="Tether USD",
        symbol="USDT",
        decimals=6,
        token_type=TokenType.NO_RETURN,
    )
    owner = "0xHarvester"
    spender = "0xStrategy"

    SafeERC20Wrapper.force_approve(token, owner, spender, 1_000)
    assert token.allowances[owner][spender] == 1_000

    SafeERC20Wrapper.force_approve(token, owner, spender, 2_000)
    assert token.allowances[owner][spender] == 2_000


def test_batch_harvest_length_mismatch_raises_error():
    """Validates that array length mismatch raises ValueError."""
    token = TokenModel(
        name="Standard USD",
        symbol="SUSD",
        decimals=18,
        token_type=TokenType.STANDARD,
    )
    harvester = BatchYieldHarvesterModel("0xHarvester")

    with pytest.raises(ValueError, match="Array lengths mismatch"):
        harvester.batch_harvest_yield([token, token], ["0xAlice"], [100, 200])


def test_zero_amount_and_empty_recipient_raise_error():
    """Validates that zero amount or empty recipient raises SafeTransferError."""
    token = TokenModel(
        name="Standard USD",
        symbol="SUSD",
        decimals=18,
        token_type=TokenType.STANDARD,
    )
    token.mint("0xHarvester", 1_000)
    harvester = BatchYieldHarvesterModel("0xHarvester")

    with pytest.raises(SafeTransferError, match="zero amount"):
        harvester.harvest_yield(token, "0xAlice", 0)

    with pytest.raises(SafeTransferError, match="zero address"):
        harvester.harvest_yield(token, "", 100)


def test_insufficient_balance_raises_error():
    """Validates that harvest exceeding available balance raises SafeTransferError."""
    token = TokenModel(
        name="Standard USD",
        symbol="SUSD",
        decimals=18,
        token_type=TokenType.STANDARD,
    )
    token.mint("0xHarvester", 500)
    harvester = BatchYieldHarvesterModel("0xHarvester")

    with pytest.raises(SafeTransferError, match="insufficient balance"):
        harvester.harvest_yield(token, "0xAlice", 1_000)


def test_formal_verification_suite():
    """Validates that all mathematical formal verification invariants pass."""
    report = SafeTransferFormalVerifier.run_all_verifications()
    assert report["all_passed"]
    assert report["no_silent_failures"]
    assert report["non_standard_support"]
    assert report["vulnerable_harvester_reverts"]
    assert report["conservation_of_supply"]
    assert report["force_approve_transition"]
