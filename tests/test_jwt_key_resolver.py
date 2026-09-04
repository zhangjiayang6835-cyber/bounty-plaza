import pytest
from scripts.jwt_key_resolver import (
    JWTKeyResolver,
    InsecureKeyPathError,
    JWTKeyResolutionError,
)


def test_jwt_key_resolver_success():
    resolver = JWTKeyResolver({
        "auth-key-2026-v1": b"secret_key_v1_bytes_32bits_1234",
        "auth-key-2026-v2": b"secret_key_v2_bytes_32bits_5678",
    })

    key = resolver.resolve_key("auth-key-2026-v1")
    assert key == b"secret_key_v1_bytes_32bits_1234"


def test_jwt_key_resolver_blocks_path_traversal():
    resolver = JWTKeyResolver({"key-1": b"valid_key"})

    # Common path traversal attacks attempting to read /etc/passwd or /dev/null
    traversal_payloads = [
        "../../etc/passwd",
        "/dev/null",
        "..\\..\\windows\\win.ini",
        "key/../secret",
        "../../../dev/null",
        ".hidden_key",
        "key\x00extra",
    ]

    for attack in traversal_payloads:
        with pytest.raises(InsecureKeyPathError) as excinfo:
            resolver.resolve_key(attack)
        assert "Path traversal sequence detected" in str(excinfo.value) or "Invalid 'kid' format" in str(excinfo.value)


def test_jwt_key_resolver_rejects_unwhitelisted_kid():
    resolver = JWTKeyResolver({"prod-key-01": b"super_secret"})

    with pytest.raises(JWTKeyResolutionError) as excinfo:
        resolver.resolve_key("nonexistent-key-99")
    assert "Unknown Key ID" in str(excinfo.value)
    assert "prod-key-01" in str(excinfo.value)


def test_jwt_key_resolver_rejects_empty_or_whitespace():
    resolver = JWTKeyResolver({"k1": b"secret"})

    with pytest.raises(JWTKeyResolutionError):
        resolver.resolve_key("")

    with pytest.raises(JWTKeyResolutionError):
        resolver.resolve_key("   ")

    with pytest.raises(JWTKeyResolutionError):
        resolver.resolve_key(None)


def test_register_key_validates_kid():
    resolver = JWTKeyResolver()
    resolver.register_key("new-key-1", b"material")
    assert "new-key-1" in resolver.registered_kids
    assert resolver.resolve_key("new-key-1") == b"material"

    with pytest.raises(InsecureKeyPathError):
        resolver.register_key("../invalid", b"material")

    with pytest.raises(ValueError):
        resolver.register_key("valid-name", b"")
