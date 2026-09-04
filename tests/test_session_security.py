import pytest
from scripts.session_security import (
    SessionManager,
    SessionSecurityError,
)


def test_create_session_and_cookie_attributes():
    manager = SessionManager(
        cookie_name="__Host-sessionid",
        session_ttl_seconds=1800,
        enforce_secure_cookie=True,
        same_site="Strict",
    )
    sid, cookie_header = manager.create_session(initial_data={"guest_cart": [1, 2]})

    assert len(sid) > 20
    assert f"__Host-sessionid={sid}" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "Secure" in cookie_header
    assert "SameSite=Strict" in cookie_header
    assert "Max-Age=1800" in cookie_header

    data = manager.get_session_data(sid)
    assert data == {"guest_cart": [1, 2]}


def test_session_id_in_url_rejected():
    manager = SessionManager()

    # Attack: User tricked into opening link with attacker-predefined session ID
    malicious_url = "https://bountyplaza.dev/login?sessionid=attacker_chosen_token_123"
    with pytest.raises(SessionSecurityError) as excinfo:
        manager.extract_session_id(request_url=malicious_url)
    assert "Session Fixation Attempt Blocked" in str(excinfo.value)
    assert "sessionid" in str(excinfo.value)

    # Variant parameter names
    with pytest.raises(SessionSecurityError):
        manager.extract_session_id("https://bountyplaza.dev/dashboard?sid=123")


def test_extract_session_id_from_valid_cookie():
    manager = SessionManager(cookie_name="__Host-sessionid")
    sid, _ = manager.create_session()

    cookie_header = f"theme=dark; __Host-sessionid={sid}; analytics_id=xyz"
    extracted = manager.extract_session_id(
        request_url="https://bountyplaza.dev/profile",
        cookie_header=cookie_header,
    )
    assert extracted == sid


def test_regenerate_session_upon_login():
    manager = SessionManager()
    guest_sid, _ = manager.create_session(initial_data={"search_history": ["security"]})

    # Successful login occurs -> session must regenerate
    new_sid, new_cookie = manager.regenerate_session(
        old_session_id=guest_sid,
        authenticated_data={"user_id": 42, "role": "admin"},
    )

    # Invariant: Old session ID must be invalidated completely
    assert new_sid != guest_sid
    assert manager.get_session_data(guest_sid) is None

    # Invariant: Data must be safely preserved and updated
    new_data = manager.get_session_data(new_sid)
    assert new_data["search_history"] == ["security"]
    assert new_data["user_id"] == 42
    assert new_data["role"] == "admin"
