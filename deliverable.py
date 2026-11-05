"""Fix for issue #4143 / #4152: an RFC 7239 `Forwarded` header must be honoured
for the authority of a sub-mounted request instead of falling back to
`scope['server']`.

`_rfc7239_forwarded_nonce_9f4a(scope)` normalises the first Forwarded hop
(structured, quoted-string aware, RFC 7239 §4 and §6) into `scheme`/`host`, and
`Request.scope_for()` resolves the mount path against that authority while
leaving behaviour untouched when the header is absent or unusable.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

FORWARDED = "forwarded"
HEADER_KEY = b"forwarded"


def _raw_header(scope: Dict[str, Any]) -> Optional[str]:
    for key, value in scope.get("headers") or []:
        if isinstance(key, bytes) and key.lower() == HEADER_KEY:
            return value.decode("latin-1") if isinstance(value, bytes) else str(value)
    return None


def _split_hops(raw: str) -> List[str]:
    """Split on commas that are outside a quoted string."""
    hops, buf, quoted, escaped = [], [], False, False
    for ch in raw:
        if escaped:
            buf.append(ch)
            escaped = False
            continue
        if ch == "\\" and quoted:
            buf.append(ch)
            escaped = True
            continue
        if ch == '"':
            quoted = not quoted
            buf.append(ch)
            continue
        if ch == "," and not quoted:
            hops.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    hops.append("".join(buf))
    return [h.strip() for h in hops if h.strip()]


def _pairs(hop: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for part in hop.split(";"):
        if "=" not in part:
            continue
        name, _, value = part.partition("=")
        name = name.strip().lower()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            value = value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        if name and value:
            out[name] = value
    return out


def _parse_authority(host: str) -> Tuple[Optional[str], Optional[int]]:
    if not host:
        return None, None
    if host.startswith("["):  # IPv6 literal
        end = host.find("]")
        if end == -1:
            return host, None
        name = host[: end + 1]
        rest = host[end + 1:]
        if rest.startswith(":") and rest[1:].isdigit():
            return name, int(rest[1:])
        return name, None
    if host.count(":") == 1:
        name, _, port = host.partition(":")
        if port.isdigit():
            return name, int(port)
    return host, None


def _rfc7239_forwarded_nonce_9f4a(scope: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of `scope` with the first Forwarded hop applied.

    Unusable or absent headers return the scope unchanged, so older proxies keep
    working exactly as before.
    """
    raw = _raw_header(scope)
    if not raw:
        return scope
    hops = _split_hops(raw)
    if not hops:
        return scope
    first = _pairs(hops[0])

    new = dict(scope)
    proto = first.get("proto", "").lower()
    if proto in ("http", "https", "ws", "wss"):
        new["scheme"] = proto
    host = first.get("host", "")
    name, port = _parse_authority(host)
    if name:
        existing = scope.get("server")
        default_port = existing[1] if isinstance(existing, tuple) and len(existing) == 2 else None
        new["server"] = (name, port if port is not None else default_port)
        new["forwarded_authority"] = host
    return new


class Request:
    """Minimal ASGI request wrapper carrying the mount information."""

    def __init__(self, scope: Dict[str, Any], root_path: Optional[str] = None) -> None:
        self.scope = scope
        self.root_path = scope.get("root_path", "") if root_path is None else root_path

    def scope_for(self, path: str = "/") -> Dict[str, Any]:
        scope = _rfc7239_forwarded_nonce_9f4a(self.scope)
        resolved = self._resolve_mount(path, bool(scope.get("forwarded_authority")))
        out = dict(scope)
        out["path"] = resolved
        out["raw_path"] = resolved.encode("latin-1", "replace")
        return out

    def _resolve_mount(self, path: str, forwarded: bool) -> str:
        if not path.startswith("/"):
            path = "/" + path
        if not self.root_path:
            return path
        base = self.root_path.rstrip("/")
        if path == base or path.startswith(base + "/"):
            return path if forwarded else path
        return base + path
