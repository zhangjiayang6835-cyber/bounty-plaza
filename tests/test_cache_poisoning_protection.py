import pytest
from scripts.cache_poisoning_protection import (
    CacheKeyManager,
    CacheSecurityError,
    DANGEROUS_UNKEYED_HEADERS,
)


def test_sanitize_upstream_headers_strips_untrusted_unkeyed_headers():
    manager = CacheKeyManager(trusted_proxies=["10.0.0.1"])
    raw_headers = {
        "Host": "bountyplaza.dev",
        "X-Forwarded-Host": "attacker.evil.com",
        "X-Original-URL": "/admin/drain",
        "X-Rewrite-URL": "/malicious/exploit.js",
        "User-Agent": "Mozilla/5.0",
        "Accept-Encoding": "gzip, deflate",
    }

    # Request from untrusted peer (e.g., 192.168.1.50)
    cleaned = manager.sanitize_upstream_headers(raw_headers, client_ip="192.168.1.50")
    for dangerous_h in DANGEROUS_UNKEYED_HEADERS:
        assert dangerous_h not in [k.lower() for k in cleaned.keys()]

    assert "Host" in cleaned
    assert "User-Agent" in cleaned
    assert "Accept-Encoding" in cleaned


def test_sanitize_upstream_headers_preserves_trusted_proxy_headers():
    manager = CacheKeyManager(trusted_proxies=["10.0.0.1"])
    raw_headers = {
        "Host": "bountyplaza.dev",
        "X-Forwarded-Host": "legit-internal-gateway.bountyplaza.dev",
    }

    # Request from verified trusted proxy
    cleaned = manager.sanitize_upstream_headers(raw_headers, client_ip="10.0.0.1")
    assert cleaned.get("X-Forwarded-Host") == "legit-internal-gateway.bountyplaza.dev"


def test_compute_cache_key_deterministic_and_query_normalized():
    manager = CacheKeyManager()
    headers = {
        "Host": "bountyplaza.dev",
        "Accept-Encoding": "gzip, br",
        "Accept-Language": "en-US,en;q=0.9",
    }

    # Differing query parameter order should resolve to identical cache key
    url_a = "https://bountyplaza.dev/api/data?b=2&a=1&c=3"
    url_b = "https://bountyplaza.dev/api/data?c=3&a=1&b=2"

    key_a = manager.compute_cache_key("GET", url_a, headers)
    key_b = manager.compute_cache_key("GET", url_b, headers)

    assert key_a == key_b
    assert len(key_a) == 64  # SHA256 hex string


def test_compute_cache_key_rejects_uncacheable_methods():
    manager = CacheKeyManager()
    with pytest.raises(CacheSecurityError, match="uncacheable"):
        manager.compute_cache_key("POST", "/submit", {})

    with pytest.raises(CacheSecurityError, match="uncacheable"):
        manager.compute_cache_key("DELETE", "/resource", {})


def test_build_vary_header_normalization():
    manager = CacheKeyManager(keyed_headers=["Accept-Encoding", "Accept-Language"])
    vary_header = manager.build_vary_header(["Cookie", "X-Custom-Variant"])

    # Ensure all variants are comma-separated and sorted
    assert "accept-encoding" in vary_header
    assert "accept-language" in vary_header
    assert "cookie" in vary_header
    assert "x-custom-variant" in vary_header
