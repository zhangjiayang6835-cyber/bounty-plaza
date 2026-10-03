"""
Canonical URL normalization for agent card discovery.

Requirements:
- Strip default ports (80 for http, 443 for https).
- Lowercase scheme and host.
- Remove redundant consecutive slashes in the path without breaking scheme separator.
- Preserve path, query parameters, and fragments.
"""

import re
from urllib.parse import urlsplit, urlunsplit

from .errors import InvalidUrlError

_DEFAULT_PORTS: dict[str, int] = {
    "http": 80,
    "https": 443,
    "ws": 80,
    "wss": 443,
    "ftp": 21,
}


def canonicalize_url(url: str) -> str:
    """
    Produce a canonicalized representation of the given URL.

    Args:
        url: Raw URL string.

    Returns:
        Canonical URL string.

    Raises:
        InvalidUrlError: If the URL is empty or malformed.
    """
    if not url or not isinstance(url, str):
        raise InvalidUrlError("URL must be a non-empty string", url=str(url))

    stripped = url.strip()
    if not stripped:
        raise InvalidUrlError("URL cannot be empty or whitespace only", url=url)

    try:
        parts = urlsplit(stripped)
    except Exception as exc:
        raise InvalidUrlError(f"Malformed URL structure: {exc}", url=url) from exc

    scheme = parts.scheme.lower()
    if not scheme:
        raise InvalidUrlError("URL is missing a valid scheme (e.g., 'https')", url=url)

    if not parts.netloc:
        raise InvalidUrlError("URL is missing network location (host)", url=url)

    # Parse hostname and port
    try:
        hostname = parts.hostname
        port = parts.port
    except ValueError as exc:
        raise InvalidUrlError(f"Invalid host or port in URL: {exc}", url=url) from exc

    if not hostname:
        raise InvalidUrlError("URL hostname could not be parsed", url=url)

    hostname = hostname.lower()

    # Determine canonical netloc
    default_port = _DEFAULT_PORTS.get(scheme)
    if port is None or port == default_port:
        netloc = hostname
    else:
        netloc = f"{hostname}:{port}"

    # Handle userinfo if present
    if "@" in parts.netloc:
        userinfo = parts.netloc.rsplit("@", 1)[0]
        netloc = f"{userinfo}@{netloc}"

    # Normalize path: collapse multiple slashes while preserving root /
    path = parts.path
    if path:
        # Replace multiple consecutive slashes with a single slash
        normalized_path = re.sub(r"/+", "/", path)
    else:
        normalized_path = ""

    return urlunsplit((scheme, netloc, normalized_path, parts.query, parts.fragment))
