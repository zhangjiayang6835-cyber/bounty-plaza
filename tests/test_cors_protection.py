import pytest
from scripts.cors_protection import CORSSecurityManager, CORSValidationError

def test_wildcard_with_credentials_rejected():
    with pytest.raises(CORSValidationError) as excinfo:
        CORSSecurityManager(allowed_origins=["*"], allow_credentials=True)
    assert "Wildcard '*' origin is forbidden" in str(excinfo.value)

def test_whitelist_origin_allowed():
    manager = CORSSecurityManager(
        allowed_origins=["https://trusted.bountyplaza.dev", "https://app.bountyplaza.dev"],
        allow_credentials=True
    )
    assert manager.is_origin_allowed("https://trusted.bountyplaza.dev") is True
    assert manager.is_origin_allowed("https://app.bountyplaza.dev") is True
    assert manager.is_origin_allowed("https://evil.attacker.com") is False
    assert manager.is_origin_allowed("null") is False
    assert manager.is_origin_allowed(None) is False

def test_cors_headers_whitelisted_origin_with_credentials():
    manager = CORSSecurityManager(
        allowed_origins=["https://trusted.bountyplaza.dev"],
        allow_credentials=True
    )
    headers = manager.build_cors_headers("https://trusted.bountyplaza.dev")
    assert headers["Vary"] == "Origin"
    assert headers["Access-Control-Allow-Origin"] == "https://trusted.bountyplaza.dev"
    assert headers["Access-Control-Allow-Credentials"] == "true"

def test_cors_headers_untrusted_origin_rejected():
    manager = CORSSecurityManager(
        allowed_origins=["https://trusted.bountyplaza.dev"],
        allow_credentials=True
    )
    headers = manager.build_cors_headers("https://evil.attacker.com")
    assert headers["Vary"] == "Origin"
    assert "Access-Control-Allow-Origin" not in headers
    assert "Access-Control-Allow-Credentials" not in headers

def test_cors_preflight_headers():
    manager = CORSSecurityManager(
        allowed_origins=["https://trusted.bountyplaza.dev"],
        allow_credentials=True,
        allowed_methods=["GET", "POST", "PUT"],
        allowed_headers=["Authorization", "Content-Type"],
        max_age=3600
    )
    headers = manager.build_cors_headers("https://trusted.bountyplaza.dev", is_preflight=True)
    assert headers["Vary"] == "Origin"
    assert headers["Access-Control-Allow-Origin"] == "https://trusted.bountyplaza.dev"
    assert headers["Access-Control-Allow-Credentials"] == "true"
    assert headers["Access-Control-Allow-Methods"] == "GET, POST, PUT"
    assert headers["Access-Control-Allow-Headers"] == "Authorization, Content-Type"
    assert headers["Access-Control-Max-Age"] == "3600"
