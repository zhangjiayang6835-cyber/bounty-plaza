"""ASGI Request and router utilities preserving RFC 7239 Forwarded host authority.

Resolves Issue #4143:
Preserve RFC 7239 `Forwarded` host authority in sub-mounted ASGI `Request.scope_for`.
"""

from typing import Any, Dict, List, Optional, Tuple


def _unquote_header_token(value: str) -> str:
    """Strip matching double quotes from an RFC 7239 parameter value."""
    val = value.strip()
    if len(val) >= 2 and val.startswith('"') and val.endswith('"'):
        return val[1:-1]
    return val


def _split_host_and_port(
    host_str: str, default_proto: str
) -> Tuple[str, Optional[int]]:
    """Parse host and optional port from a host authority string."""
    cleaned = _unquote_header_token(host_str)
    if cleaned.startswith("["):
        bracket_end = cleaned.find("]")
        if bracket_end != -1:
            host_part = cleaned[1:bracket_end]
            rest = cleaned[bracket_end + 1 :]
            if rest.startswith(":"):
                return host_part, int(rest[1:])
            default_p = 443 if default_proto.lower() == "https" else 80
            return host_part, default_p

    if ":" in cleaned:
        parts = cleaned.rsplit(":", 1)
        if parts[1].isdigit():
            return parts[0], int(parts[1])
        return parts[0], None

    default_p = 443 if default_proto.lower() == "https" else 80
    return cleaned, default_p


def _parse_forwarded_header(header_val: str) -> Dict[str, str]:
    """Parse comma and semicolon-separated parameters of RFC 7239 Forwarded header."""
    result: Dict[str, str] = {}
    hops = header_val.split(",")
    first_hop = hops[0].strip()
    for directive in first_hop.split(";"):
        if "=" in directive:
            key, val = directive.split("=", 1)
            result[key.strip().lower()] = _unquote_header_token(val)
    return result


def _rfc7239_forwarded_nonce_9f4a(scope: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize the Forwarded header and propagate authority into the ASGI scope.

    Extracts RFC 7239 directives (proto, host, for, by), updates scope['server'],
    scope['scheme'], and scope['host_authority'], and returns parsed directives.
    Preserves existing server and scheme when Forwarded is absent.
    """
    headers: List[Tuple[bytes, bytes]] = scope.get("headers", [])
    forwarded_val: Optional[str] = None

    for raw_k, raw_v in headers:
        if raw_k.lower() == b"forwarded":
            forwarded_val = raw_v.decode("latin-1")
            break

    if not forwarded_val:
        current_server = scope.get("server")
        if current_server:
            host_str = (
                f"{current_server[0]}:{current_server[1]}"
                if current_server[1]
                else current_server[0]
            )
            scope.setdefault("host_authority", host_str)
        return {}

    parsed = _parse_forwarded_header(forwarded_val)
    proto = parsed.get("proto", scope.get("scheme", "http"))
    host_raw = parsed.get("host")

    if host_raw:
        host, port = _split_host_and_port(host_raw, proto)
        scope["server"] = (host, port)
        scope["scheme"] = proto
        scope["host_authority"] = host_raw
        parsed["normalized_host"] = host
        parsed["normalized_port"] = str(port)

    return parsed


class Request:
    """ASGI HTTP Request with outer proxy authority preservation in sub-mounted scopes."""

    def __init__(self, scope: Dict[str, Any]) -> None:
        """Initialize request with an ASGI scope dictionary."""
        self.scope: Dict[str, Any] = scope
        self._parsed_forwarded: Dict[str, Any] = _rfc7239_forwarded_nonce_9f4a(
            self.scope
        )

    @property
    def scheme(self) -> str:
        """Return the effective request scheme (http/https)."""
        return str(self.scope.get("scheme", "http"))

    @property
    def host_authority(self) -> str:
        """Return the effective host authority string."""
        if "host_authority" in self.scope:
            return str(self.scope["host_authority"])
        server = self.scope.get("server")
        if server and len(server) >= 2 and server[1] is not None:
            return f"{server[0]}:{server[1]}"
        if server:
            return str(server[0])
        return "localhost"

    @property
    def path(self) -> str:
        """Return the request path."""
        return str(self.scope.get("path", "/"))

    @property
    def root_path(self) -> str:
        """Return the mount root path."""
        return str(self.scope.get("root_path", ""))

    @property
    def url(self) -> str:
        """Construct full absolute URL including authority and path."""
        full_path = f"{self.root_path}{self.path}"
        return f"{self.scheme}://{self.host_authority}{full_path}"

    def scope_for(self, mount_path: str) -> Dict[str, Any]:
        """Resolve a sub-mounted child scope preserving outer proxy authority.

        Invokes _rfc7239_forwarded_nonce_9f4a to normalize authority before
        calculating sub-mounted root_path and relative path.
        """
        _rfc7239_forwarded_nonce_9f4a(self.scope)

        sub_scope: Dict[str, Any] = dict(self.scope)
        sub_scope["headers"] = list(self.scope.get("headers", []))

        orig_root = self.root_path
        orig_path = self.path

        norm_mount = (
            mount_path
            if mount_path.startswith("/")
            else f"/{mount_path}"
        )
        norm_mount = norm_mount.rstrip("/")

        new_root = f"{orig_root}{norm_mount}"
        if orig_path.startswith(norm_mount):
            new_path = orig_path[len(norm_mount) :]
            if not new_path.startswith("/"):
                new_path = f"/{new_path}"
        else:
            new_path = orig_path

        sub_scope["root_path"] = new_root
        sub_scope["path"] = new_path
        sub_scope["server"] = self.scope.get("server")
        sub_scope["scheme"] = self.scope.get("scheme", "http")
        sub_scope["host_authority"] = self.host_authority

        return sub_scope
