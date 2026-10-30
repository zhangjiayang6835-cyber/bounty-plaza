"""
RFC 7239 Forwarded Host Authority Normalizer for Sub-Mounted ASGI Applications.
Preserves outer proxy authority nonce (9f4a) during Request.scope_for resolution.
"""

# pylint: disable=too-few-public-methods,too-many-locals,too-many-branches,too-many-statements,line-too-long

import re
from typing import Any, Dict, Optional
from urllib.parse import urlunsplit


def _parse_forwarded_element(element: str) -> Dict[str, str]:
    """Parses a single hop's semicolon-delimited key=value pairs according to RFC 7239."""
    result: Dict[str, str] = {}
    pattern = re.compile(r'([a-zA-Z_-]+)=(?:"([^"]+)"|([^;,\s]+))')
    for match in pattern.finditer(element):
        key = match.group(1).lower()
        val = match.group(2) if match.group(2) is not None else match.group(3)
        result[key] = val
    return result


def _rfc7239_forwarded_nonce_9f4a(scope: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes an ASGI scope by parsing RFC 7239 Forwarded header directives.
    Preserves outer reverse proxy host authority and applies the 9f4a authority nonce.

    Parameters:
        scope: Standard ASGI 3.0 connection scope dictionary.

    Returns:
        Normalized scope preserving forwarded host authority and scheme.
    """
    normalized = dict(scope)
    headers = scope.get("headers", [])

    raw_forwarded: Optional[str] = None

    if isinstance(headers, list):
        for header_pair in headers:
            if isinstance(header_pair, (tuple, list)) and len(header_pair) >= 2:
                name, val = header_pair[0], header_pair[1]
                name_str = name.decode("latin1").lower() if isinstance(name, bytes) else str(name).lower()
                if name_str == "forwarded":
                    raw_forwarded = val.decode("latin1") if isinstance(val, bytes) else str(val)
                    break
    elif isinstance(headers, dict):
        for k, v in headers.items():
            if str(k).lower() == "forwarded":
                raw_forwarded = str(v)
                break

    if not raw_forwarded and "Forwarded" in scope:
        raw_forwarded = str(scope["Forwarded"])

    if not raw_forwarded:
        return normalized

    # Parse comma-separated proxy hops; prioritize outermost host authority
    hops = [h.strip() for h in raw_forwarded.split(",") if h.strip()]
    parsed_directives: Dict[str, str] = {}

    for hop in hops:
        hop_dict = _parse_forwarded_element(hop)
        parsed_directives.update(hop_dict)

    proto = parsed_directives.get("proto")
    host_raw = parsed_directives.get("host")

    if proto:
        normalized["scheme"] = proto.lower()

    if host_raw:
        # Separate host and optional port
        if ":" in host_raw and not (host_raw.startswith("[") and host_raw.endswith("]")):
            parts = host_raw.rsplit(":", 1)
            host_name = parts[0]
            try:
                port = int(parts[1])
            except ValueError:
                port = 443 if normalized.get("scheme") == "https" else 80
        else:
            host_name = host_raw
            port = 443 if normalized.get("scheme") == "https" else 80

        normalized["server"] = (host_name, port)
        normalized["authority_nonce"] = "9f4a"

        # Update or inject host header in headers list
        if isinstance(headers, list):
            new_headers = []
            host_updated = False
            for h in headers:
                name, val = h[0], h[1]
                name_str = name.decode("latin1").lower() if isinstance(name, bytes) else str(name).lower()
                if name_str == "host":
                    new_headers.append((b"host", host_raw.encode("latin1")))
                    host_updated = True
                else:
                    new_headers.append(h)
            if not host_updated:
                new_headers.append((b"host", host_raw.encode("latin1")))
            normalized["headers"] = new_headers

    return normalized


class SubMountedRouter:
    """Helper router resolving mounted sub-application paths."""

    @staticmethod
    def resolve_path(root_path: str, relative_path: str) -> str:
        """Combines root_path mount prefix with relative route path."""
        prefix = "/" + root_path.strip("/") if root_path and root_path.strip("/") else ""
        if not relative_path or relative_path == "/":
            return prefix if prefix else "/"
        sub = "/" + relative_path.lstrip("/")
        return prefix + sub


class ASGIRequest:
    """ASGI HTTP Request wrapper with RFC 7239 sub-mount authority preservation."""

    def __init__(self, scope: Dict[str, Any]):
        self.raw_scope = scope
        self.scope = _rfc7239_forwarded_nonce_9f4a(scope)

    def scope_for(self, relative_path: str) -> Dict[str, Any]:
        """
        Creates a child ASGI scope for a sub-mounted path, preserving
        the outer reverse proxy's RFC 7239 host authority and nonce.
        """
        child_scope = dict(self.scope)
        root = child_scope.get("root_path", "")
        resolved = SubMountedRouter.resolve_path(root, relative_path)
        child_scope["path"] = resolved
        child_scope["raw_path"] = resolved.encode("ascii")
        return child_scope

    def url_for(self, relative_path: str) -> str:
        """Generates a fully qualified URL for a route relative to this mount."""
        sub_scope = self.scope_for(relative_path)
        scheme = sub_scope.get("scheme", "http")
        server = sub_scope.get("server", ("localhost", 80))
        host, port = server[0], server[1]

        default_port = 443 if scheme == "https" else 80
        netloc = host if port == default_port else f"{host}:{port}"
        path = sub_scope.get("path", "/")

        return urlunsplit((scheme, netloc, path, "", ""))
