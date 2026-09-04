import pytest
from scripts.ldap_security import (
    escape_filter_value,
    escape_dn_value,
    validate_bind_credentials,
    build_user_search_filter,
    AnonymousBindAttemptError,
    LDAPSecurityError,
)


def test_escape_filter_rfc4515_characters():
    # Common LDAP injection vectors
    assert escape_filter_value("admin*)(uid=*))") == r"admin\2a\29\28uid=\2a\29\29"
    assert escape_filter_value(r"domain\user") == r"domain\5cuser"
    assert escape_filter_value("test\x00inject") == r"test\00inject"
    assert escape_filter_value("path/to/resource") == r"path\2fto\2fresource"


def test_escape_dn_rfc4514_characters():
    assert escape_dn_value("Doe, John") == r"Doe\, John"
    assert escape_dn_value("CN=Admin+User") == r"CN=Admin\+User"
    assert escape_dn_value(" Quotes \"Inside\" ") == r"\ Quotes \"Inside\"\ "
    assert escape_dn_value("#leading_hash") == r"\#leading_hash"


def test_build_user_search_filter_prevents_injection():
    malicious_input = "*)(uid=*))"
    filter_str = build_user_search_filter(malicious_input)
    assert filter_str == r"(&(objectClass=inetOrgPerson)(uid=\2a\29\28uid=\2a\29\29))"
    assert ")(uid=*))" not in filter_str


def test_validate_bind_credentials_blocks_anonymous_bind():
    # Empty username
    with pytest.raises(AnonymousBindAttemptError) as excinfo:
        validate_bind_credentials("", "secret123")
    assert "Username must not be empty" in str(excinfo.value)

    # Whitespace username
    with pytest.raises(AnonymousBindAttemptError):
        validate_bind_credentials("   ", "secret123")

    # None username
    with pytest.raises(AnonymousBindAttemptError):
        validate_bind_credentials(None, "secret123")

    # Empty password (unauthenticated bind attempt)
    with pytest.raises(AnonymousBindAttemptError) as excinfo:
        validate_bind_credentials("admin", "")
    assert "Password must not be empty" in str(excinfo.value)

    with pytest.raises(AnonymousBindAttemptError):
        validate_bind_credentials("admin", "   ")

    with pytest.raises(AnonymousBindAttemptError):
        validate_bind_credentials("admin", None)


def test_validate_bind_credentials_valid():
    u, p = validate_bind_credentials("  alice  ", "secretPass99!")
    assert u == "alice"
    assert p == "secretPass99!"


def test_type_errors():
    with pytest.raises(TypeError):
        escape_filter_value(123)
    with pytest.raises(TypeError):
        escape_dn_value(None)
    with pytest.raises(LDAPSecurityError):
        build_user_search_filter("")
