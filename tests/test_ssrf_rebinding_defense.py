"""Unit and security test suite for DNS Rebinding SSRF Neutralization Engine.
Resolves Issue #307: Blind SSRF via DNS Rebinding Bypass ($150 USD).
"""

import pytest
from scripts.ssrf_rebinding_defense import (
    SafeSSRFProtectionEngine,
    PrivateIPAddressError,
    InvalidSchemeError,
    RedirectLimitExceededError,
    is_ip_prohibited,
)


def test_ip_prohibited_checker():
    # Public IPs allowed
    assert is_ip_prohibited("8.8.8.8") is False
    assert is_ip_prohibited("1.1.1.1") is False
    assert is_ip_prohibited("93.184.216.34") is False

    # Private RFC 1918 IPs prohibited
    assert is_ip_prohibited("127.0.0.1") is True
    assert is_ip_prohibited("10.0.0.1") is True
    assert is_ip_prohibited("172.16.5.10") is True
    assert is_ip_prohibited("192.168.1.1") is True

    # Cloud metadata prohibited
    assert is_ip_prohibited("169.254.169.254") is True
    assert is_ip_prohibited("169.254.1.1") is True

    # IPv6 Loopback & ULA prohibited
    assert is_ip_prohibited("::1") is True
    assert is_ip_prohibited("fc00::1") is True
    assert is_ip_prohibited("fe80::1") is True


def test_valid_public_domain_plan():
    # Mock DNS resolver returning public IP
    def mock_dns(host, port):
        return ["93.184.216.34"]

    engine = SafeSSRFProtectionEngine(dns_resolver=mock_dns)
    plan = engine.build_safe_request_plan("https://example.com/api/data")

    assert plan["scheme"] == "https"
    assert plan["hostname"] == "example.com"
    assert plan["port"] == 443
    assert plan["pinned_ip"] == "93.184.216.34"
    assert plan["host_header"] == "example.com"


def test_dns_rebinding_resolution_to_private_ip_blocked():
    """Simulates a DNS Rebinding attack where a domain resolves to 169.254.169.254."""
    def mock_rebind_dns(host, port):
        return ["169.254.169.254"]

    engine = SafeSSRFProtectionEngine(dns_resolver=mock_rebind_dns)
    with pytest.raises(PrivateIPAddressError, match="DNS Rebinding / SSRF blocked"):
        engine.build_safe_request_plan("http://evil-rebind.internal.attacker.com/latest/meta-data")


def test_dns_rebinding_dual_stack_mixed_ips_blocked():
    """Domain resolves to both a public IP and an internal loopback IP: must fail closed."""
    def mock_mixed_dns(host, port):
        return ["93.184.216.34", "127.0.0.1"]

    engine = SafeSSRFProtectionEngine(dns_resolver=mock_mixed_dns)
    with pytest.raises(PrivateIPAddressError, match="DNS Rebinding / SSRF blocked"):
        engine.build_safe_request_plan("http://dual-resolve.attacker.com/")


def test_prohibited_schemes_blocked():
    engine = SafeSSRFProtectionEngine()
    disallowed_urls = [
        "file:///etc/passwd",
        "gopher://127.0.0.1:6379/_flushall",
        "dict://127.0.0.1:11211/stat",
        "ftp://internal.ftp.corp/secrets",
    ]
    for url in disallowed_urls:
        with pytest.raises(InvalidSchemeError, match="Prohibited URL scheme"):
            engine.build_safe_request_plan(url)


def test_redirect_to_metadata_endpoint_blocked():
    def mock_dns(host, port):
        if host == "legit.com":
            return ["93.184.216.34"]
        if host == "metadata.internal":
            return ["169.254.169.254"]
        return ["8.8.8.8"]

    engine = SafeSSRFProtectionEngine(dns_resolver=mock_dns)
    initial_plan = engine.build_safe_request_plan("https://legit.com/fetch")

    # Redirect location targets cloud metadata
    with pytest.raises(PrivateIPAddressError, match="DNS Rebinding / SSRF blocked"):
        engine.validate_redirect(
            current_url=initial_plan["target_url"],
            redirect_location="http://metadata.internal/latest/meta-data",
            current_redirect_count=initial_plan["redirect_count"],
        )


def test_redirect_limit_exceeded():
    def mock_dns(host, port):
        return ["93.184.216.34"]

    engine = SafeSSRFProtectionEngine(max_redirects=2, dns_resolver=mock_dns)
    plan1 = engine.build_safe_request_plan("https://legit.com/hop0")
    plan2 = engine.validate_redirect(plan1["target_url"], "/hop1", plan1["redirect_count"])
    plan3 = engine.validate_redirect(plan2["target_url"], "/hop2", plan2["redirect_count"])

    with pytest.raises(RedirectLimitExceededError, match="Maximum redirects"):
        engine.validate_redirect(plan3["target_url"], "/hop3", plan3["redirect_count"])
