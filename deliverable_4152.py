"""RFC 7239 Forwarded header parser and ASGI Request scope normalizer (#4152).

This module provides utilities to parse and extract client authority from the
RFC 7239 `Forwarded` HTTP header and preserve that host and protocol authority
across sub-mounted ASGI applications.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

FORWARDED_HEADER_KEY = b"forwarded"
VALID_SCHEMES = ("http", "https", "ws", "wss")


def _extract_raw_header(scope: Dict[str, Any]) -> Optional[str]:
    """Extract the first Forwarded header value from an ASGI scope.

    Supports both bytes and str keys/values in scope['headers'].
    """
    headers = scope.get("headers")
    if not headers:
        return None
    for item in headers:
        if isinstance(item, (tuple, list)) and len(item) == 2:
            key, val = item
            k_bytes = key.lower() if isinstance(key, bytes) else str(key).lower().encode("latin-1")
            if k_bytes == FORWARDED_HEADER_KEY:
                if isinstance(val, bytes):
                    return val.decode("latin-1")
                return str(val)
    return None


def _split_hops(raw_value: str) -> List[str]:
    """Split Forwarded header by commas that are outside quoted strings."""
    hops: List[str] = []
    buffer: List[str] = []
    in_quotes = False
    is_escaped = False

    for char in raw_value:
        if is_escaped:
            buffer.append(char)
            is_escaped = False
            continue
        if char == "\\" and in_quotes:
            buffer.append(char)
            is_escaped = True
            continue
        if char == '"':
            in_quotes = not in_quotes
            buffer.append(char)
            continue
        if char == "," and not in_quotes:
            hops.append("".join(buffer))
            buffer = []
            continue
        buffer.append(char)

    hops.append("".join(buffer))
    return [h.strip() for h in hops if h.strip()]


def _parse_directives(hop: str) -> Dict[str, str]:
    """Parse semicolon-separated parameters of a single Forwarded hop."""
    directives: Dict[str, str] = {}
    for part in hop.split(";"):
        if "=" not in part:
            continue
        name, _, val = part.partition("=")
        param_name = name.strip().lower()
        param_value = val.strip()

        # Handle quoted-string and unescape backslash sequences
        if len(param_value) >= 2 and param_value[0] == '"' and param_value[-1] == '"':
            inner = param_value[1:-1]
            unescaped: List[str] = []
            esc = False
            for char in inner:
                if esc:
                    unescaped.append(char)
                    esc = False
                elif char == "\\":
                    esc = True
                else:
                    unescaped.append(char)
            param_value = "".join(unescaped)

        if param_name and param_value:
            directives[param_name] = param_value

    return directives


def _parse_host_authority(host: str) -> Tuple[Optional[str], Optional[int]]:
    """Parse a host string into host name/literal and optional port.

    Supports domain names, explicit ports, and IPv6 literals such as
    `[2001:db8::1]:443`.
    """
    if not host:
        return None, None

    # Handle bracketed IPv6 literal
    if host.startswith("["):
        closing_bracket = host.find("]")
        if closing_bracket == -1:
            return host, None
        name = host[: closing_bracket + 1]
        suffix = host[closing_bracket + 1:]
        if suffix.startswith(":") and suffix[1:].isdigit():
            return name, int(suffix[1:])
        return name, None

    # Handle standard host:port
    if host.count(":") == 1:
        name, _, port_str = host.partition(":")
        if port_str.isdigit():
            return name, int(port_str)

    return host, None


def _rfc7239_forwarded_nonce_9f4a(scope: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize ASGI scope with outer proxy authority from RFC 7239 Forwarded.

    Parses the first Forwarded hop. If missing, empty, or malformed, the original
    scope is returned unchanged for backwards compatibility.
    """
    raw_header = _extract_raw_header(scope)
    if not raw_header:
        return scope

    hops = _split_hops(raw_header)
    if not hops:
        return scope

    first_hop = _parse_directives(hops[0])
    if not first_hop:
        return scope

    new_scope = dict(scope)
    proto = first_hop.get("proto", "").lower()
    if proto in VALID_SCHEMES:
        new_scope["scheme"] = proto

    host_value = first_hop.get("host", "")
    host_name, port = _parse_host_authority(host_value)
    if host_name:
        existing_server = scope.get("server")
        default_port = (
            existing_server[1]
            if isinstance(existing_server, tuple) and len(existing_server) == 2
            else None
        )
        resolved_port = port if port is not None else default_port
        new_scope["server"] = (host_name, resolved_port)
        new_scope["forwarded_authority"] = host_value
        new_scope["host_authority"] = host_value

    return new_scope


class Request:
    """Minimal ASGI request wrapper handling sub-mounted route scope derivation."""

    def __init__(self, scope: Dict[str, Any], root_path: Optional[str] = None) -> None:
        self.scope = scope
        self.root_path = scope.get("root_path", "") if root_path is None else root_path

    def resolve_path(self, path: str = "/") -> str:
        """Resolve mount prefix against relative sub-path."""
        return self._resolve_mount_path(path, self.root_path)

    def scope_for(self, path: Optional[str] = None) -> Dict[str, Any]:
        """Derive sub-mounted scope preserving outer Forwarded authority."""
        if isinstance(self, dict):
            target_scope = self
            mount_root = target_scope.get("root_path", "")
            target_path = path if path is not None else "/"
        else:
            target_scope = self.scope
            mount_root = self.root_path
            target_path = path if path is not None else "/"

        normalized = _rfc7239_forwarded_nonce_9f4a(target_scope)
        resolved_path = self._resolve_mount_path(target_path, mount_root)

        derived = dict(normalized)
        derived["path"] = resolved_path
        derived["raw_path"] = resolved_path.encode("latin-1", "replace")
        return derived

    @staticmethod
    def _resolve_mount_path(path: str, root_path: str) -> str:
        """Resolve mount prefix against relative sub-path."""
        clean_path = path if path.startswith("/") else f"/{path}"
        if not root_path:
            return clean_path
        base = root_path.rstrip("/")
        if clean_path == base or clean_path.startswith(f"{base}/"):
            return clean_path
        return f"{base}{clean_path}"
