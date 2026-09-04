"""Unit and security test suite for Clickjacking Defense & Secondary Confirmation.
Resolves Issue #312: Clickjacking via X-Frame-Options Missing -> Crypto Withdraw ($120 USD).
"""

import time
import pytest
from scripts.clickjacking_protection import (
    ClickjackingDefenseMiddleware,
    CryptoWithdrawalService,
    MissingConfirmationError,
    InvalidConfirmationTokenError,
)


@pytest.fixture
def middleware():
    return ClickjackingDefenseMiddleware(secret_key="ultra_secure_clickjacking_key_312", confirmation_ttl_seconds=10)


@pytest.fixture
def withdrawal_service(middleware):
    return CryptoWithdrawalService(defense=middleware)


def test_apply_security_headers_default(middleware):
    headers = {"Server": "CustomEdge"}
    secured = middleware.apply_security_headers(headers)

    assert secured["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in secured["Content-Security-Policy"]
    assert secured["X-Content-Type-Options"] == "nosniff"
    assert secured["Server"] == "CustomEdge"


def test_apply_security_headers_append_existing_csp(middleware):
    headers = {"Content-Security-Policy": "default-src 'self'"}
    secured = middleware.apply_security_headers(headers)

    assert secured["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in secured["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in secured["Content-Security-Policy"]


def test_direct_clickjacking_attempt_without_secondary_confirmation(withdrawal_service):
    """An attacker overlays transparent iframe trying to trigger 1-click withdrawal."""
    with pytest.raises(MissingConfirmationError, match="Secondary confirmation token required"):
        withdrawal_service.process_withdrawal_request(
            user_id="usr_victim",
            asset="ETH",
            amount=5.0,
            destination_address="0xAttackerWallet1234567890abcdef",
            confirmation_token=None,
        )


def test_successful_withdrawal_with_secondary_confirmation(withdrawal_service, middleware):
    user_id = "usr_crypto_whale"
    asset = "USDC"
    amount = 50000.0
    dest = "0x71C56538b1529405e324298108c6422896504245"

    _, token = middleware.generate_withdrawal_confirmation_challenge(
        user_id=user_id,
        asset=asset,
        amount=amount,
        destination_address=dest,
    )

    res = withdrawal_service.process_withdrawal_request(
        user_id=user_id,
        asset=asset,
        amount=amount,
        destination_address=dest,
        confirmation_token=token,
    )

    assert res["status"] == "APPROVED"
    assert res["amount"] == 50000.0
    assert res["headers"]["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in res["headers"]["Content-Security-Policy"]


def test_tampered_confirmation_token_rejected(withdrawal_service, middleware):
    user_id = "usr_alice"
    asset = "SOL"
    amount = 10.0
    dest = "7XwP6eF..."

    _, token = middleware.generate_withdrawal_confirmation_challenge(
        user_id=user_id,
        asset=asset,
        amount=amount,
        destination_address=dest,
    )

    # Attacker tries to alter amount to 100.0 or redirect destination
    with pytest.raises(InvalidConfirmationTokenError, match="amount mismatch|does not match"):
        withdrawal_service.process_withdrawal_request(
            user_id=user_id,
            asset=asset,
            amount=100.0,
            destination_address=dest,
            confirmation_token=token,
        )


def test_confirmation_token_replay_blocked(withdrawal_service, middleware):
    user_id = "usr_bob"
    asset = "BTC"
    amount = 1.0
    dest = "bc1qxyz..."

    _, token = middleware.generate_withdrawal_confirmation_challenge(
        user_id=user_id,
        asset=asset,
        amount=amount,
        destination_address=dest,
    )

    # First withdrawal succeeds
    withdrawal_service.process_withdrawal_request(
        user_id=user_id,
        asset=asset,
        amount=amount,
        destination_address=dest,
        confirmation_token=token,
    )

    # Replaying the same token must be rejected
    with pytest.raises(InvalidConfirmationTokenError, match="already been consumed"):
        withdrawal_service.process_withdrawal_request(
            user_id=user_id,
            asset=asset,
            amount=amount,
            destination_address=dest,
            confirmation_token=token,
        )


def test_expired_confirmation_token_rejected():
    short_middleware = ClickjackingDefenseMiddleware(secret_key="short_key", confirmation_ttl_seconds=1)
    service = CryptoWithdrawalService(defense=short_middleware)

    _, token = short_middleware.generate_withdrawal_confirmation_challenge(
        user_id="usr_quick",
        asset="USDT",
        amount=100.0,
        destination_address="0xTarget",
    )

    time.sleep(1.2)
    with pytest.raises(InvalidConfirmationTokenError, match="expired"):
        service.process_withdrawal_request(
            user_id="usr_quick",
            asset="USDT",
            amount=100.0,
            destination_address="0xTarget",
            confirmation_token=token,
        )
