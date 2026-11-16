import pytest
from middleware.forwarded_fix import preserve_forwarded_host

def test_preserve_forwarded_host():
    scope = {
        "type": "http",
        "headers": [(b"forwarded", b"host=example.com;proto=https")]
    }
    
    updated_scope = preserve_forwarded_host(scope)
    
    headers = dict(updated_scope["headers"])
    assert headers[b"host"] == b"example.com"
    assert updated_scope["client_host"] == "example.com"

def test_no_forwarded_header():
    scope = {"type": "http", "headers": []}
    updated_scope = preserve_forwarded_host(scope)
    assert b"host" not in dict(updated_scope["headers"])
