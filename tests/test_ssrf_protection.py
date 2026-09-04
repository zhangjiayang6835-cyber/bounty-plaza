import socket

import pytest

from scripts.ssrf_protection import UnsafeURLError, resolve_public_url


def test_rejects_private_dns_answer(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))],
    )
    with pytest.raises(UnsafeURLError):
        resolve_public_url("http://rebind.example/resource")


def test_rejects_mixed_public_and_private_answers(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.8", 80)),
        ],
    )
    with pytest.raises(UnsafeURLError):
        resolve_public_url("http://rebind.example/resource")


def test_accepts_public_host(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))],
    )
    assert resolve_public_url("http://example.com/resource")[1] == ["93.184.216.34"]


@pytest.mark.parametrize("url", ["//example.com", "file:///etc/passwd", "http://user:pass@example.com"])
def test_rejects_ambiguous_urls(url):
    with pytest.raises(UnsafeURLError):
        resolve_public_url(url)
