import pytest
from scripts.cache_deception_protection import (
    CacheDeceptionManager,
)


def test_cache_deception_attack_blocked_on_sensitive_route():
    manager = CacheDeceptionManager()

    # Attack vector: Attacker tricks authenticated user to visit /account/settings/nonexistent.css
    # Server returns user profile JSON or HTML.
    attack_url = "/account/settings/nonexistent.css"
    headers = manager.evaluate_response_cache_policy(
        request_path=attack_url,
        content_type="text/html; charset=utf-8",
        is_authenticated=True,
    )

    assert "no-store" in headers["Cache-Control"]
    assert "private" in headers["Cache-Control"]
    assert headers["X-Content-Type-Options"] == "nosniff"

    # CDN must refuse to cache this response
    response_headers = {
        "Content-Type": "text/html",
        "Cache-Control": headers["Cache-Control"],
    }
    assert manager.should_cdn_cache(attack_url, response_headers) is False


def test_static_extension_with_dynamic_content_no_store():
    manager = CacheDeceptionManager()

    # Unauthenticated user requesting a path ending in .css that returns JSON
    path = "/api/user/info.css"
    headers = manager.evaluate_response_cache_policy(
        request_path=path,
        content_type="application/json",
        is_authenticated=False,
    )

    assert "no-store" in headers["Cache-Control"]
    assert "private" in headers["Cache-Control"]


def test_legitimate_static_asset_allowed_cache():
    manager = CacheDeceptionManager()

    path = "/assets/styles/main.css"
    headers = manager.evaluate_response_cache_policy(
        request_path=path,
        content_type="text/css",
        is_authenticated=False,
    )

    assert "public" in headers["Cache-Control"]
    assert "max-age=86400" in headers["Cache-Control"]

    cdn_headers = {
        "Content-Type": "text/css",
        "Cache-Control": headers["Cache-Control"],
    }
    assert manager.should_cdn_cache(path, cdn_headers) is True


def test_cdn_cache_decision_rejects_html_even_with_public_cache_control():
    manager = CacheDeceptionManager()

    # Even if misconfigured to public, HTML must not be cached as a static asset
    cdn_headers = {
        "Content-Type": "text/html",
        "Cache-Control": "public, max-age=3600",
    }
    assert manager.should_cdn_cache("/profile.css", cdn_headers) is False
