"""Unit tests for CL.TE HTTP Request Smuggling & Cache Poisoning Defense Subsystem.
Validates Issue #495 / zhangjiayang6835-cyber/ai-research#1172 ($200 USD).
"""

import pytest
import sys
from pathlib import Path

# Add bounty-plaza root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.cl_te_smuggling_guard import (
    HttpSmugglingDefenseGateway,
    HttpRequestMessage,
    HttpProtocolVersion,
    ValidationAction,
    WebCachePoisoningSanitizer,
)


def test_reject_coexistence_of_transfer_encoding_and_content_length():
    gateway = HttpSmugglingDefenseGateway(strict_reject_te_cl_coexistence=True)

    # Classic CL.TE attack payload headers
    req = HttpRequestMessage(
        method="POST",
        uri="/search",
        protocol=HttpProtocolVersion.HTTP_1_1,
        headers={
            "Host": "victim.corp",
            "Content-Length": "13",
            "Transfer-Encoding": "chunked",
        },
        raw_header_lines=[
            "Host: victim.corp",
            "Content-Length: 13",
            "Transfer-Encoding: chunked",
        ],
        body=b"0\r\n\r\nSMUGGLED",
    )

    result = gateway.inspect_and_sanitize(req)
    assert result.action == ValidationAction.REJECT_400
    assert result.status_code == 400
    assert "Coexistence of Transfer-Encoding and Content-Length forbidden" in result.reason
    assert gateway.poisoning_attempts_blocked == 1


def test_reject_obfuscated_and_duplicate_transfer_encoding():
    gateway = HttpSmugglingDefenseGateway()

    # Obfuscation: Transfer-Encoding with whitespace before colon
    req_ws = HttpRequestMessage(
        method="POST",
        uri="/login",
        protocol=HttpProtocolVersion.HTTP_1_1,
        headers={"Host": "victim.corp", "Transfer-Encoding": "chunked"},
        raw_header_lines=[
            "Host: victim.corp",
            "Transfer-Encoding : chunked",
        ],
    )
    res_ws = gateway.inspect_and_sanitize(req_ws)
    assert res_ws.action == ValidationAction.REJECT_400
    assert "whitespace before colon" in res_ws.reason

    # Duplicate Transfer-Encoding headers (TE.TE desync vector)
    req_dup = HttpRequestMessage(
        method="POST",
        uri="/comment",
        protocol=HttpProtocolVersion.HTTP_1_1,
        headers={"Host": "victim.corp", "Transfer-Encoding": "chunked"},
        raw_header_lines=[
            "Host: victim.corp",
            "Transfer-Encoding: chunked",
            "Transfer-Encoding: identity",
        ],
    )
    res_dup = gateway.inspect_and_sanitize(req_dup)
    assert res_dup.action == ValidationAction.REJECT_400
    assert "Multiple or duplicate" in res_dup.reason

    # Unsupported or malformed token
    req_bad_tok = HttpRequestMessage(
        method="POST",
        uri="/api",
        protocol=HttpProtocolVersion.HTTP_1_1,
        headers={"Host": "victim.corp", "Transfer-Encoding": "xchunked"},
        raw_header_lines=["Host: victim.corp", "Transfer-Encoding: xchunked"],
    )
    res_tok = gateway.inspect_and_sanitize(req_bad_tok)
    assert res_tok.action == ValidationAction.REJECT_400
    assert "Unsupported or obfuscated" in res_tok.reason


def test_http10_downgrade_prevention():
    gateway = HttpSmugglingDefenseGateway(disallow_http10_downgrade=True)

    req_http10 = HttpRequestMessage(
        method="GET",
        uri="/index.html",
        protocol=HttpProtocolVersion.HTTP_1_0,
        headers={"Host": "victim.corp"},
    )
    res = gateway.inspect_and_sanitize(req_http10)
    assert res.action == ValidationAction.REJECT_400
    assert "HTTP/1.0 downgrade disabled" in res.reason


def test_http2_safe_binary_framing():
    gateway = HttpSmugglingDefenseGateway()

    req_http2 = HttpRequestMessage(
        method="POST",
        uri="/data",
        protocol=HttpProtocolVersion.HTTP_2,
        headers={
            ":authority": "victim.corp",
            ":method": "POST",
            ":path": "/data",
            "content-type": "application/json",
        },
        body=b'{"query": "valid"}',
    )
    res = gateway.inspect_and_sanitize(req_http2)
    assert res.action == ValidationAction.ALLOW
    assert res.status_code == 200
    assert res.is_http2_safe is True


def test_web_cache_poisoning_sanitizer():
    # Header unkeyed header stripping
    poisoned_headers = {
        "Host": "evil.attacker.com",
        "X-Forwarded-Host": "evil.attacker.com",
        "X-Original-URL": "/admin",
        "X-Rewrite-URL": "/admin",
        "Accept": "text/html",
    }
    allowed_hosts = {"victim.corp", "www.victim.corp"}

    cleaned = WebCachePoisoningSanitizer.sanitize_upstream_request(poisoned_headers, allowed_hosts)
    assert "x-forwarded-host" not in cleaned
    assert "x-original-url" not in cleaned
    assert "x-rewrite-url" not in cleaned
    assert cleaned["host"] in allowed_hosts

    # Safe deterministic cache key generation
    key1 = WebCachePoisoningSanitizer.generate_safe_cache_key("GET", "victim.corp", "//app//home", "b=2&a=1")
    key2 = WebCachePoisoningSanitizer.generate_safe_cache_key("get", "VICTIM.CORP", "/app/home", "a=1&b=2")
    assert key1 == key2
    assert key1 == "GET|victim.corp|/app/home|a=1&b=2"
