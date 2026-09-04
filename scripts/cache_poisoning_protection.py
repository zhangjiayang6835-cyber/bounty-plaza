"""Web Cache Poisoning Defense & Cache Key Normalization Engine.
Resolves Issue #78: Web Cache Poisoning via Unkeyed Header ($150).
"""

import hashlib
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit


class CacheSecurityError(ValueError):
    """Raised when request headers contain malicious unkeyed cache poisoning vectors."""
    pass


# Headers frequently abused for unkeyed cache poisoning
DANGEROUS_UNKEYED_HEADERS: Set[str] = {
    "x-forwarded-host",
    "x-forwarded-scheme",
    "x-original-url",
    "x-rewrite-url",
    "x-forwarded-prefix",
    "x-host",
}


class CacheKeyManager:
    """Computes deterministic cache keys and cleanses unkeyed headers to defeat cache poisoning."""

    def __init__(
        self,
        trusted_proxies: Optional[List[str]] = None,
        keyed_headers: Optional[List[str]] = None,
        canonical_host: str = "bountyplaza.dev",
    ):
        self.trusted_proxies = set(trusted_proxies or ["127.0.0.1", "::1"])
        # Headers that MUST be included in the cache key calculation if they affect the response
        self.keyed_headers = [h.lower() for h in (keyed_headers or ["accept-encoding", "accept-language"])]
        self.canonical_host = canonical_host.lower()

    def sanitize_upstream_headers(
        self,
        headers: Dict[str, str],
        client_ip: str = "127.0.0.1"
    ) -> Dict[str, str]:
        """Strip or neutralize unkeyed forward headers from untrusted clients/proxies.

        Args:
            headers: Incoming raw request headers.
            client_ip: IP address of the immediate connecting peer.

        Returns:
            Sanitized headers safe for upstream forwarding and application consumption.
        """
        sanitized: Dict[str, str] = {}
        is_trusted = client_ip in self.trusted_proxies

        for key, value in headers.items():
            k_lower = key.lower().strip()
            # If not coming from a verified trusted proxy, strip dangerous unkeyed headers
            if not is_trusted and k_lower in DANGEROUS_UNKEYED_HEADERS:
                continue

            sanitized[key] = value

        return sanitized

    def compute_cache_key(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        client_ip: str = "127.0.0.1"
    ) -> str:
        """Compute a tamper-proof canonical cache key incorporating all variance dimensions.

        Args:
            method: HTTP method (e.g. GET, HEAD).
            url: Full request URL or path.
            headers: Incoming request headers.
            client_ip: Client IP address.

        Returns:
            SHA256 hex digest representing the unique cache bucket.
        """
        # Only GET and HEAD requests should be cached
        norm_method = method.upper().strip()
        if norm_method not in ("GET", "HEAD"):
            raise CacheSecurityError(f"Method '{norm_method}' is uncacheable")

        parsed = urlsplit(url)
        path = parsed.path or "/"

        # Normalize query parameters alphabetically to avoid cache fragmentation
        query_dict = parse_qs(parsed.query, keep_blank_values=True)
        sorted_query = urlencode(sorted((k, sorted(v)) for k, v in query_dict.items()), doseq=True)

        # Normalize host: discard attacker-supplied X-Forwarded-Host from untrusted origins
        safe_headers = self.sanitize_upstream_headers(headers, client_ip=client_ip)
        header_map = {k.lower(): v.strip() for k, v in safe_headers.items()}

        host = header_map.get("host", self.canonical_host)

        # Include keyed headers (e.g. Accept-Encoding, Accept-Language)
        keyed_parts = []
        for kh in sorted(self.keyed_headers):
            val = header_map.get(kh, "")
            keyed_parts.append(f"{kh}:{val}")

        key_payload = f"{norm_method}|{host}|{path}|{sorted_query}|{'|'.join(keyed_parts)}"
        return hashlib.sha256(key_payload.encode("utf-8")).hexdigest()

    def build_vary_header(self, additional_vary: Optional[List[str]] = None) -> str:
        """Construct normalized Vary response header ensuring intermediate caches partition correctly."""
        all_vary = set(self.keyed_headers)
        if additional_vary:
            for item in additional_vary:
                all_vary.add(item.lower().strip())

        return ", ".join(sorted(all_vary))
