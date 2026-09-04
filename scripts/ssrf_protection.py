"""Validate outbound HTTP targets against SSRF and DNS-rebinding attacks."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit


class UnsafeURLError(ValueError):
    """Raised when a URL resolves to a non-public or otherwise unsafe address."""


def resolve_public_url(url: str) -> tuple[str, list[str]]:
    """Return the normalized URL and its validated addresses.

    Every A/AAAA answer is checked.  Rejecting if *any* answer is private
    prevents a DNS rebinding response from selecting an internal address.
    Callers should resolve and connect within the same controlled operation.
    """
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UnsafeURLError("only absolute HTTP(S) URLs are allowed")
    if parsed.username or parsed.password:
        raise UnsafeURLError("userinfo in URLs is not allowed")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise UnsafeURLError("invalid port") from exc
    infos = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
    addresses = sorted({info[4][0] for info in infos})
    if not addresses:
        raise UnsafeURLError("hostname has no addresses")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise UnsafeURLError(f"non-public address resolved: {address}")
    return parsed.geturl(), addresses

