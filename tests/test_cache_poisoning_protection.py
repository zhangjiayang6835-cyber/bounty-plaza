import pytest
from scripts.cache_poisoning_protection import (
    CacheKeyManager,
    CacheSecurityError,
)


def test_untrusted_unkeyed_headers_stripped():
    manager = CacheKeyManager(trusted_proxies=["127.0.0.1"])

    incoming_headers = {
        "Host": "bountyplaza.dev",
        "X-Forwarded-Host": "evil-attacker.com",
        "X-Original-URL": "/admin/secret",
        "Accept-Encoding": "gzip, deflate",
        "User-Agent": "Mozilla/5.0",
    }

    # Untrusted client IP: unkeyed forwarding headers must be purged
    cleaned = manager.sanitize_upstream_headers(incoming_headers, client_ip="203.0.113.195")
    assert "X-Forwarded-Host" not in cleaned
    assert "X-Original-URL" not in cleaned
    assert cleaned["Host"] == "bountyplaza.dev"
    assert cleaned["Accept-Encoding"] == "gzip, deflate"


def test_trusted_proxy_headers_preserved():
    manager = CacheKeyManager(trusted_proxies=["10.0.0.1"])

    headers = {
        "Host": "bountyplaza.dev",
        "X-Forwarded-Host": "app.bountyplaza.dev",
    }
    # Trusted internal proxy IP
    cleaned = manager.sanitize_upstream_headers(headers, client_ip="10.0.0.1")
    assert cleaned.get("X-Forwarded-Host") == "app.bountyplaza.dev"


def test_compute_cache_key_deterministic_and_poison_resistant():
    manager = CacheKeyManager(
        keyed_headers=["accept-encoding"],
        canonical_host="bountyplaza.dev"
    )

    legit_headers = {
        "Host": "bountyplaza.dev",
        "Accept-Encoding": "gzip",
    }
    key_legit = manager.compute_cache_key("GET", "/home?b=2&a=1", legit_headers, client_ip="203.0.113.5")

    # Attacker injects malicious X-Forwarded-Host header
    poison_headers = {
        "Host": "bountyplaza.dev",
        "X-Forwarded-Host": "evil.com",
        "Accept-Encoding": "gzip",
    }
    key_poison_attempt = manager.compute_cache_key("GET", "/home?a=1&b=2", poison_headers, client_ip="203.0.113.5")

    # The cache keys must match because:
    # 1. Unkeyed X-Forwarded-Host is stripped
    # 2. Query parameters are canonically sorted
    assert key_legit == key_poison_attempt


def test_uncacheable_method_raises():
    manager = CacheKeyManager()
    with pytest.raises(CacheSecurityError):
        manager.compute_cache_key("POST", "/submit", {})


def test_build_vary_header():
    manager = CacheKeyManager(keyed_headers=["accept-encoding", "accept-language"])
    vary = manager.build_vary_header(additional_vary=["Cookie"])
    assert "accept-encoding" in vary
    assert "accept-language" in vary
    assert "cookie" in vary
