"""ASGI Forwarded Host Authority Resolver (RFC 7239).

Resolves Issue #4171:
Preserve RFC 7239 `Forwarded` host authority in sub-mounted ASGI `Request.scope_for`.
"""

from typing import Any, Dict, Optional, Tuple


def _rfc7239_forwarded_nonce_9f4a(scope: dict) -> str:
    """Normalize and extract host authority from RFC 7239 Forwarded header.

    Parses case-insensitive header tuples from scope['headers'] looking for
    'forwarded' and extracts 'host=<authority>' (unquoting if needed).
    Returns empty string if absent or invalid.
    """
    headers = scope.get("headers", [])
    for key, val in headers:
        if isinstance(key, bytes):
            key = key.decode("latin1", errors="ignore")
        if isinstance(val, bytes):
            val = val.decode("latin1", errors="ignore")

        if key.lower() == "forwarded":
            # RFC 7239 Forwarded: for=...;proto=...;host=...
            directives = [d.strip() for d in val.split(";")]
            for directive in directives:
                if directive.lower().startswith("host="):
                    host_part = directive[5:].strip()
                    # Strip quotation marks if quoted-string
                    if (host_part.startswith('"') and host_part.endswith('"')) or (
                        host_part.startswith("'") and host_part.endswith("'")
                    ):
                        host_part = host_part[1:-1].strip()
                    return host_part
    return ""


def _rfc7239_forwarded_proto(scope: dict) -> str:
    """Normalize and extract proto/scheme from RFC 7239 Forwarded header."""
    headers = scope.get("headers", [])
    for key, val in headers:
        if isinstance(key, bytes):
            key = key.decode("latin1", errors="ignore")
        if isinstance(val, bytes):
            val = val.decode("latin1", errors="ignore")

        if key.lower() == "forwarded":
            directives = [d.strip() for d in val.split(";")]
            for directive in directives:
                if directive.lower().startswith("proto="):
                    proto_part = directive[6:].strip().strip("\"'").lower()
                    return proto_part
    return ""


def _resolve_server_and_authority(
    scope: dict, forwarded_host: str, forwarded_proto: str
) -> Tuple[Optional[Tuple[str, int]], Optional[str]]:
    """Determine server tuple and authority string based on headers or scope."""
    if forwarded_host:
        if ":" in forwarded_host:
            host_str, port_str = forwarded_host.split(":", 1)
            port = int(port_str)
        else:
            host_str = forwarded_host
            orig_server = scope.get("server")
            orig_port = orig_server[1] if orig_server else 80
            port = 443 if forwarded_proto == "https" and orig_port == 80 else orig_port
        return (host_str, port), forwarded_host

    if "server" in scope:
        server_host, server_port = scope["server"][0], scope["server"][1]
        authority = (
            f"{server_host}:{server_port}"
            if server_port not in (80, 443)
            else server_host
        )
        return scope["server"], authority

    return None, None


class SubScope:
    """Wrapped sub-mounted ASGI scope mapping."""

    def __init__(self, scope: dict):
        self._scope: dict = scope

    @property
    def scope(self) -> dict:
        """Return raw underlying scope dictionary."""
        return self._scope

    def __getitem__(self, key: str) -> Any:
        return self._scope[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._scope[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self._scope

    def get(self, key: str, default: Any = None) -> Any:
        """Get an item from the scope or return default."""
        return self._scope.get(key, default)

    def to_dict(self) -> dict:
        """Return a shallow dictionary copy of the scope."""
        return dict(self._scope)


class Router:
    """Minimal route table resolver for URL path generation."""

    def __init__(self):
        self.routes: Dict[str, str] = {}

    def add_route(self, name: str, path_pattern: str) -> None:
        """Register a URL path pattern under a route name."""
        self.routes[name] = path_pattern

    def url_path_for(self, name: str, **path_params) -> str:
        """Resolve a route pattern by name substituting path parameters."""
        if name not in self.routes:
            raise KeyError(f"Route named '{name}' not found")
        pattern = self.routes[name]
        for k, v in path_params.items():
            pattern = pattern.replace(f"{{{k}}}", str(v))
        return pattern


class Request:  # pylint: disable=too-few-public-methods
    """ASGI HTTP Request encapsulation with RFC 7239 authority preservation."""

    def __init__(self, scope: dict, router: Optional[Router] = None):
        self.scope: dict = scope
        self.router: Optional[Router] = router

    def scope_for(
        self,
        path_or_name: Optional[str] = None,
        *,
        path: Optional[str] = None,
        name: Optional[str] = None,
        **path_params,
    ) -> SubScope:
        """Resolve a sub-mounted route scope while preserving RFC 7239 Forwarded host.

        Supports both instance calls `req.scope_for(...)` and class calls
        `Request.scope_for(scope, ...)`.
        """
        if isinstance(self, Request):
            scope = self.scope
            router = self.router
        elif isinstance(self, dict):
            scope = self
            router = None
        else:
            raise TypeError("scope_for expects Request instance or scope dict")

        target_path = (
            path
            if path is not None
            else (
                path_or_name
                if path_or_name and str(path_or_name).startswith("/")
                else None
            )
        )
        target_name = (
            name
            if name is not None
            else (
                path_or_name
                if path_or_name and not str(path_or_name).startswith("/")
                else None
            )
        )
        return Request._build_scope(
            scope, path=target_path, name=target_name, router=router, **path_params
        )

    @classmethod
    def _build_scope(
        cls,
        scope: dict,
        path: Optional[str] = None,
        name: Optional[str] = None,
        router: Optional[Router] = None,
        **path_params,
    ) -> SubScope:
        sub = dict(scope)

        forwarded_host = _rfc7239_forwarded_nonce_9f4a(scope)
        forwarded_proto = _rfc7239_forwarded_proto(scope)

        server_tuple, authority = _resolve_server_and_authority(
            scope, forwarded_host, forwarded_proto
        )
        if server_tuple is not None:
            sub["server"] = server_tuple
        if authority is not None:
            sub["host_authority"] = authority

        if forwarded_proto:
            sub["scheme"] = forwarded_proto
        elif "scheme" in scope:
            sub["scheme"] = scope["scheme"]
        else:
            sub["scheme"] = "http"

        if path is not None:
            sub["path"] = path
        elif name is not None and router is not None:
            sub["path"] = router.url_path_for(name, **path_params)

        return SubScope(sub)
