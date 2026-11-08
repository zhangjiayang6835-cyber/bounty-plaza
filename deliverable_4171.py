"""RFC 7239 Forwarded header parser and ASGI request authority preservation.

Resolves Issue #4171:
Preserves RFC 7239 Forwarded host authority in sub-mounted ASGI Request.scope_for.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


def unquote_token(value: str) -> str:
    """Strip matching quotes and process backslash-escaped characters in RFC 7239 values."""
    val = value.strip()
    if len(val) >= 2 and val.startswith('"') and val.endswith('"'):
        inner = val[1:-1]
        out: List[str] = []
        idx = 0
        length = len(inner)
        while idx < length:
            char = inner[idx]
            if char == "\\" and idx + 1 < length:
                idx += 1
                out.append(inner[idx])
            else:
                out.append(char)
            idx += 1
        return "".join(out)
    return val


def split_quoted_string(text: str, delimiter: str) -> List[str]:
    """Split text by delimiter while respecting quoted-strings and backslash escapes."""
    items: List[str] = []
    current: List[str] = []
    in_quotes = False
    escape = False

    for char in text:
        if escape:
            current.append(char)
            escape = False
        elif char == "\\":
            current.append(char)
            if in_quotes:
                escape = True
        elif char == '"':
            in_quotes = not in_quotes
            current.append(char)
        elif char == delimiter and not in_quotes:
            item = "".join(current).strip()
            if item:
                items.append(item)
            current = []
        else:
            current.append(char)

    last_item = "".join(current).strip()
    if last_item:
        items.append(last_item)
    return items


def split_host_and_port(
    host_str: str, default_proto: str = "http"
) -> Tuple[str, Optional[int]]:
    """Parse host and port from a host authority string, supporting IPv6 bracket notation."""
    cleaned = unquote_token(host_str)
    default_port = 443 if default_proto.lower() == "https" else 80

    if cleaned.startswith("["):
        bracket_end = cleaned.find("]")
        if bracket_end != -1:
            host_part = cleaned[1:bracket_end]
            rest = cleaned[bracket_end + 1 :]
            if rest.startswith(":"):
                port_str = rest[1:]
                if port_str.isdigit():
                    return host_part, int(port_str)
            return host_part, default_port

    if ":" in cleaned:
        parts = cleaned.rsplit(":", 1)
        if parts[1].isdigit():
            return parts[0], int(parts[1])
        if cleaned.count(":") > 1:
            return cleaned, default_port
        return parts[0], None

    return cleaned, default_port


def parse_forwarded_element(element_str: str) -> Dict[str, str]:
    """Parse a single forwarded element (semicolon-separated directives)."""
    result: Dict[str, str] = {}
    directives = split_quoted_string(element_str, ";")
    for directive in directives:
        if "=" in directive:
            key, val = directive.split("=", 1)
            norm_key = key.strip().lower()
            unquoted_val = unquote_token(val)
            if norm_key == "proto":
                result[norm_key] = unquoted_val.lower()
            else:
                result[norm_key] = unquoted_val
    return result


def parse_forwarded_header(header_val: str) -> List[Dict[str, str]]:
    """Parse an RFC 7239 Forwarded header value into a list of element dictionaries."""
    elements = split_quoted_string(header_val, ",")
    parsed_list: List[Dict[str, str]] = []
    for elem in elements:
        parsed_elem = parse_forwarded_element(elem)
        if parsed_elem:
            parsed_list.append(parsed_elem)
    return parsed_list


def parse_forwarded_first_hop(header_val: str) -> Dict[str, str]:
    """Parse the first hop (leftmost element) from an RFC 7239 Forwarded header value."""
    elements = split_quoted_string(header_val, ",")
    if not elements:
        return {}
    return parse_forwarded_element(elements[0])


@dataclass(frozen=True)
class ForwardedElement:
    """Represents a single parsed hop in an RFC 7239 Forwarded header field."""

    by: Optional[str] = None
    for_param: Optional[str] = None
    host: Optional[str] = None
    proto: Optional[str] = None
    extensions: Optional[Dict[str, str]] = None

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieve a directive value by case-insensitive key name."""
        norm_key = key.lower()
        if norm_key == "by":
            return self.by if self.by is not None else default
        if norm_key == "for":
            return self.for_param if self.for_param is not None else default
        if norm_key == "host":
            return self.host if self.host is not None else default
        if norm_key == "proto":
            return self.proto if self.proto is not None else default
        if self.extensions:
            return self.extensions.get(norm_key, default)
        return default

    def to_dict(self) -> Dict[str, str]:
        """Convert the element directives into a dictionary."""
        result: Dict[str, str] = {}
        if self.by is not None:
            result["by"] = self.by
        if self.for_param is not None:
            result["for"] = self.for_param
        if self.host is not None:
            result["host"] = self.host
        if self.proto is not None:
            result["proto"] = self.proto
        if self.extensions:
            result.update(self.extensions)
        return result


def normalize_asgi_scope(scope: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize the Forwarded header and propagate authority into the ASGI scope."""
    headers: List[Tuple[bytes, bytes]] = scope.get("headers", [])
    forwarded_val: Optional[str] = None

    forwarded_parts: List[str] = []
    for raw_k, raw_v in headers:
        if raw_k.lower() == b"forwarded":
            forwarded_parts.append(raw_v.decode("latin-1"))

    if forwarded_parts:
        forwarded_val = ", ".join(forwarded_parts)

    if not forwarded_val:
        current_server = scope.get("server")
        if current_server:
            if len(current_server) > 1 and current_server[1] is not None:
                host_str = f"{current_server[0]}:{current_server[1]}"
            else:
                host_str = str(current_server[0])
            scope.setdefault("host_authority", host_str)
        return {}

    parsed = parse_forwarded_first_hop(forwarded_val)
    proto = parsed.get("proto", scope.get("scheme", "http"))
    host_raw = parsed.get("host")

    if host_raw:
        host, port = split_host_and_port(host_raw, proto)
        scope["server"] = (host, port)
        scope["scheme"] = proto
        scope["host_authority"] = host_raw
        parsed["normalized_host"] = host
        parsed["normalized_port"] = str(port)
    elif "proto" in parsed:
        scope["scheme"] = proto

    return parsed


# Backward compatibility aliases
_unquote_header_token = unquote_token
_split_host_and_port = split_host_and_port
_parse_forwarded_header = parse_forwarded_first_hop
_rfc7239_forwarded_nonce_9f4a = normalize_asgi_scope


class Request:
    """ASGI HTTP Request with outer proxy authority preservation in sub-mounted scopes."""

    def __init__(self, scope: Dict[str, Any]) -> None:
        """Initialize request with an ASGI scope dictionary."""
        self.scope: Dict[str, Any] = scope
        self._parsed_forwarded: Dict[str, Any] = normalize_asgi_scope(self.scope)

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
        if server and len(server) >= 1:
            return str(server[0])
        headers = self.scope.get("headers", [])
        for raw_k, raw_v in headers:
            if raw_k.lower() == b"host":
                return raw_v.decode("latin-1")
        default_host = "localhost"
        return default_host

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
        authority = self.host_authority
        target_scheme = self.scheme
        constructed_url = f"{target_scheme}://{authority}{full_path}"
        return constructed_url

    @property
    def method(self) -> str:
        """Return the HTTP method."""
        return str(self.scope.get("method", "GET"))

    @property
    def headers(self) -> List[Tuple[bytes, bytes]]:
        """Return the list of raw ASGI header tuples."""
        return list(self.scope.get("headers", []))

    def scope_for(self, mount_path: str) -> Dict[str, Any]:
        """Resolve a sub-mounted child scope preserving outer proxy authority."""
        normalize_asgi_scope(self.scope)

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
