"""Comprehensive unit test suite for OAuth 2.0 CSRF Defense, Session State & PKCE Engine.
Resolves Issue #296: OAuth 2.0 CSRF -> Account Takeover via State Bypass ($150).
"""

import time
import pytest
from scripts.oauth_security import (
    OAuthSecurityManager,
    InvalidOAuthStateError,
    PKCEValidationError,
    generate_code_verifier,
    compute_code_challenge_s256,
)


@pytest.fixture
def manager():
    return OAuthSecurityManager(secret_key="ultra_secure_oauth_secret_key_testing_value", state_ttl_seconds=10)


def test_pkce_code_verifier_length_and_charset():
    verifier = generate_code_verifier(64)
    assert len(verifier) == 64
    # Valid RFC 7636 unreserved characters
    assert all(c.isalnum() or c in "-._~" for c in verifier)


def test_pkce_code_verifier_invalid_length():
    with pytest.raises(ValueError, match="between 43 and 128"):
        generate_code_verifier(30)
    with pytest.raises(ValueError, match="between 43 and 128"):
        generate_code_verifier(150)


def test_pkce_code_challenge_derivation():
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    # RFC 7636 Appendix B test vector:
    # verifier: dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk
    # challenge: E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM
    expected_challenge = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    derived = compute_code_challenge_s256(verifier)
    assert derived == expected_challenge


def test_create_authorization_request(manager):
    session_id = "sess_user_9921_alpha"
    query, state, verifier = manager.create_authorization_request(
        session_id=session_id,
        client_id="client_xyz123",
        redirect_uri="https://app.example.com/oauth/callback",
    )

    assert "client_id=client_xyz123" in query
    assert "response_type=code" in query
    assert "code_challenge_method=S256" in query
    assert f"state={state}" in query
    assert len(verifier) == 64


def test_successful_state_verification_and_pkce(manager):
    session_id = "sess_user_valid"
    query, state, verifier = manager.create_authorization_request(
        session_id=session_id,
        client_id="client_xyz",
        redirect_uri="https://app.example.com/callback",
    )

    # State validation succeeds for same session
    assert manager.verify_callback_state(state, session_id=session_id) is True

    # PKCE validation succeeds
    assert manager.verify_pkce(session_id=session_id, code_verifier=verifier) is True


def test_csrf_state_session_mismatch_rejected(manager):
    victim_session = "victim_session_111"
    attacker_session = "attacker_session_666"

    # Attacker initiates OAuth request with their session
    _, attacker_state, _ = manager.create_authorization_request(
        session_id=attacker_session,
        client_id="client_xyz",
        redirect_uri="https://app.example.com/callback",
    )

    # Victim receives attacker's state token in CSRF attack
    with pytest.raises(InvalidOAuthStateError, match="OAuth CSRF Attack Detected"):
        manager.verify_callback_state(attacker_state, session_id=victim_session)


def test_missing_or_empty_state_rejected(manager):
    with pytest.raises(InvalidOAuthStateError, match="Missing 'state' parameter"):
        manager.verify_callback_state(None, session_id="sess_123")

    with pytest.raises(InvalidOAuthStateError, match="Missing 'state' parameter"):
        manager.verify_callback_state("", session_id="sess_123")


def test_forged_state_signature_rejected(manager):
    session_id = "sess_target"
    _, state, _ = manager.create_authorization_request(
        session_id=session_id,
        client_id="client_xyz",
        redirect_uri="https://app.example.com/callback",
    )

    parts = state.split(":")
    parts[-1] = "bad_signature_deadbeef"
    tampered_state = ":".join(parts)

    with pytest.raises(InvalidOAuthStateError, match="signature verification failed"):
        manager.verify_callback_state(tampered_state, session_id=session_id)


def test_expired_state_token_rejected():
    short_manager = OAuthSecurityManager(secret_key="short_key", state_ttl_seconds=1)
    session_id = "sess_quick"
    _, state, _ = short_manager.create_authorization_request(
        session_id=session_id,
        client_id="client_xyz",
        redirect_uri="https://app.example.com/callback",
    )

    time.sleep(1.2)
    with pytest.raises(InvalidOAuthStateError, match="expired"):
        short_manager.verify_callback_state(state, session_id=session_id)


def test_pkce_mismatched_verifier_rejected(manager):
    session_id = "sess_pkce_test"
    _, state, _ = manager.create_authorization_request(
        session_id=session_id,
        client_id="client_xyz",
        redirect_uri="https://app.example.com/callback",
    )

    wrong_verifier = generate_code_verifier(64)
    with pytest.raises(PKCEValidationError, match="code_verifier does not match"):
        manager.verify_pkce(session_id=session_id, code_verifier=wrong_verifier)
