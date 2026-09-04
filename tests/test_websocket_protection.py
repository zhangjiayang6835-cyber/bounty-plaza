import time
import pytest
from scripts.websocket_protection import (
    WebSocketSecurityManager,
    WebSocketOriginForbiddenError,
    WebSocketCSRFValidationError,
)


def test_origin_validation():
    manager = WebSocketSecurityManager(
        allowed_origins=["https://app.bountyplaza.dev", "https://bountyplaza.dev"]
    )

    assert manager.validate_origin("https://app.bountyplaza.dev") is True
    assert manager.validate_origin("https://bountyplaza.dev") is True
    assert manager.validate_origin("https://evil-attacker.com") is False
    assert manager.validate_origin("null") is False
    assert manager.validate_origin(None) is False
    assert manager.validate_origin("") is False


def test_csrf_ticket_lifecycle():
    manager = WebSocketSecurityManager(
        allowed_origins=["https://app.bountyplaza.dev"],
        token_ttl_seconds=5
    )

    session_id = "sess_user_9921_abc"
    ticket = manager.generate_csrf_ticket(session_id)

    # Valid ticket with correct session
    assert manager.verify_csrf_ticket(ticket, session_id) is True

    # Invalid session id mismatch
    assert manager.verify_csrf_ticket(ticket, "sess_different_attacker") is False

    # Tampered signature
    tampered = ticket[:-4] + "ffff"
    assert manager.verify_csrf_ticket(tampered, session_id) is False


def test_csrf_ticket_expiration():
    manager = WebSocketSecurityManager(
        allowed_origins=["https://app.bountyplaza.dev"],
        token_ttl_seconds=1
    )
    session_id = "sess_user_fast_exp"
    ticket = manager.generate_csrf_ticket(session_id)

    time.sleep(1.2)
    assert manager.verify_csrf_ticket(ticket, session_id) is False


def test_authorize_handshake_success():
    manager = WebSocketSecurityManager(
        allowed_origins=["https://app.bountyplaza.dev"]
    )
    session_id = "user_valid_sess"
    ticket = manager.generate_csrf_ticket(session_id)

    headers = {
        "Host": "bountyplaza.dev",
        "Upgrade": "websocket",
        "Connection": "Upgrade",
        "Origin": "https://app.bountyplaza.dev",
        "X-CSRF-Token": ticket,
    }

    code, msg = manager.authorize_handshake(headers, session_id=session_id)
    assert code == 101
    assert msg == "Switching Protocols"


def test_authorize_handshake_forbidden_origin():
    manager = WebSocketSecurityManager(
        allowed_origins=["https://app.bountyplaza.dev"]
    )
    session_id = "user_valid_sess"
    ticket = manager.generate_csrf_ticket(session_id)

    headers = {
        "Origin": "https://attacker.site",
        "X-CSRF-Token": ticket,
    }

    with pytest.raises(WebSocketOriginForbiddenError) as excinfo:
        manager.authorize_handshake(headers, session_id=session_id)
    assert "HTTP 403 Forbidden" in str(excinfo.value)


def test_authorize_handshake_missing_or_invalid_csrf():
    manager = WebSocketSecurityManager(
        allowed_origins=["https://app.bountyplaza.dev"]
    )
    session_id = "user_valid_sess"

    headers = {
        "Origin": "https://app.bountyplaza.dev",
        "X-CSRF-Token": "invalid_or_missing_ticket",
    }

    with pytest.raises(WebSocketCSRFValidationError) as excinfo:
        manager.authorize_handshake(headers, session_id=session_id)
    assert "Missing or invalid CSRF challenge token" in str(excinfo.value)
