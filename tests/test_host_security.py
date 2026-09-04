import pytest
from scripts.host_security import (
    HostSecurityManager,
    HostHeaderSecurityError,
)


def test_host_security_manager_whitelisting():
    manager = HostSecurityManager(
        trusted_hosts=["bountyplaza.dev", "app.bountyplaza.dev"],
        canonical_domain="bountyplaza.dev"
    )

    assert manager.is_host_trusted("bountyplaza.dev") is True
    assert manager.is_host_trusted("app.bountyplaza.dev:443") is True
    assert manager.is_host_trusted("evil.attacker.com") is False
    assert manager.is_host_trusted("attacker.com") is False
    assert manager.is_host_trusted("") is False
    assert manager.is_host_trusted(None) is False


def test_validate_host_header_raises_for_untrusted():
    manager = HostSecurityManager(trusted_hosts=["bountyplaza.dev"])

    with pytest.raises(HostHeaderSecurityError) as excinfo:
        manager.validate_host_header("attacker.com")
    assert "Untrusted Host header 'attacker.com' rejected" in str(excinfo.value)

    with pytest.raises(HostHeaderSecurityError):
        manager.validate_host_header("evil.com:8080")

    with pytest.raises(HostHeaderSecurityError):
        manager.validate_host_header("bountyplaza.dev\r\nX-Injected: true")


def test_generate_password_reset_url_poisoning_prevented():
    manager = HostSecurityManager(
        trusted_hosts=["bountyplaza.dev"],
        canonical_domain="bountyplaza.dev"
    )

    # Legitimate request
    legit_url = manager.generate_password_reset_url("secure_token_123", incoming_host="bountyplaza.dev")
    assert legit_url == "https://bountyplaza.dev/auth/reset-password?token=secure_token_123"

    # Attacker sets Host: evil-phishing.com -> must be blocked
    with pytest.raises(HostHeaderSecurityError):
        manager.generate_password_reset_url("secure_token_123", incoming_host="evil-phishing.com")

    # Default canonical fallback without incoming host
    default_url = manager.generate_password_reset_url("secret_abc")
    assert default_url == "https://bountyplaza.dev/auth/reset-password?token=secret_abc"


def test_empty_trusted_hosts_disallowed():
    with pytest.raises(HostHeaderSecurityError):
        HostSecurityManager(trusted_hosts=[])
