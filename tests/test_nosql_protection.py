import pytest
from scripts.nosql_protection import (
    sanitize_input_value,
    sanitize_query_dict,
    hash_password,
    verify_password,
    SafeAuthService,
    NoSQLInjectionError,
    AuthenticationError,
)


def test_sanitize_input_value_enforces_string():
    assert sanitize_input_value("valid_user") == "valid_user"
    assert sanitize_input_value("  alice  ") == "alice"

    with pytest.raises(NoSQLInjectionError) as excinfo:
        sanitize_input_value({"$ne": ""}, field_name="password")
    assert "must be a string" in str(excinfo.value)

    with pytest.raises(NoSQLInjectionError):
        sanitize_input_value(None, field_name="username")

    with pytest.raises(NoSQLInjectionError):
        sanitize_input_value("", field_name="username")

    with pytest.raises(NoSQLInjectionError):
        sanitize_input_value("   ", field_name="username")


def test_sanitize_query_dict_blocks_operators():
    # Top-level operator injection
    with pytest.raises(NoSQLInjectionError) as excinfo:
        sanitize_query_dict({"$where": "this.password.length > 0"})
    assert "Forbidden MongoDB operator blocked" in str(excinfo.value)

    # Nested operator injection: {"username": "admin", "password": {"$ne": ""}}
    with pytest.raises(NoSQLInjectionError) as excinfo:
        sanitize_query_dict({"username": "admin", "password": {"$ne": ""}})
    assert "Forbidden nested MongoDB operator blocked" in str(excinfo.value)


def test_password_hashing_and_verification():
    raw_pass = "SuperSecurePassword987!"
    h, salt = hash_password(raw_pass)

    assert verify_password(raw_pass, h, salt) is True
    assert verify_password("WrongPassword123", h, salt) is False


def test_safe_auth_service_flow():
    auth = SafeAuthService()
    auth.register_user("admin", "correct_horse_battery_staple", role="admin")

    # Legitimate login succeeds
    result = auth.authenticate({"username": "admin", "password": "correct_horse_battery_staple"})
    assert result["username"] == "admin"
    assert result["role"] == "admin"

    # Wrong password fails
    with pytest.raises(AuthenticationError):
        auth.authenticate({"username": "admin", "password": "invalid_password"})

    # Non-existent user fails
    with pytest.raises(AuthenticationError):
        auth.authenticate({"username": "nobody", "password": "any_password"})


def test_nosql_injection_attack_vectors_thwarted():
    auth = SafeAuthService()
    auth.register_user("admin", "top_secret_flag", role="superadmin")

    # Attack Vector 1: {"username": "admin", "password": {"$ne": ""}}
    with pytest.raises(NoSQLInjectionError):
        auth.authenticate({"username": "admin", "password": {"$ne": ""}})

    # Attack Vector 2: {"username": {"$gt": ""}, "password": {"$gt": ""}}
    with pytest.raises(NoSQLInjectionError):
        auth.authenticate({"username": {"$gt": ""}, "password": {"$gt": ""}})

    # Attack Vector 3: {"$where": "sleep(5000)"}
    with pytest.raises(NoSQLInjectionError):
        auth.authenticate({"$where": "sleep(5000)"})
