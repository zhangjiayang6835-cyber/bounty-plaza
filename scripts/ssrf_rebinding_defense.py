"""Safe HTTP Client & DNS Rebinding SSRF Neutralization Engine.
Resolves Issue #307: Blind SSRF via DNS Rebinding Bypass ($150 USD).

Implements:
1. Pinned-IP connection architecture to eliminate TOCTOU DNS Rebinding attacks.
2. Comprehensive private/reserved/link-local/cloud-metadata IP filtering (IPv4 and IPv6).
3. Strict redirect controls: validation on every hop with bounded redirect limits.
4. Allowed scheme whitelisting (http/https only; blocks file, gopher, dict, ftp).
"""

import ipaddress
import socket
from typing import Callable, List, Optional, Set, Tuple
from urllib.parse import urlparse, urljoin


class SSRFSecurityError(ValueError):
    """Base exception for SSRF security violations."""
    pass


class PrivateIPAddressError(SSRFSecurityError):
    """Raised when an address resolves to a private, loopback, or cloud-metadata network."""
    pass


class DNSResolutionError(SSRFSecurityError):
    """Raised when DNS resolution fails or returns no valid addresses."""
    pass


class RedirectLimitExceededError(SSRFSecurityError):
    """Raised when HTTP redirects exceed maximum allowed hops."""
    pass


class InvalidSchemeError(SSRFSecurityError):
    """Raised when an unapproved protocol scheme is requested."""
    pass


# Explicit cloud metadata & carrier-grade NAT network ranges
DISALLOWED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # AWS/GCP/Azure Metadata (169.254.169.254)
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),  # Shared address space / CGNAT
    ipaddress.ip_network("192.0.0.0/24"),   # IETF Protocol Assignments
    ipaddress.ip_network("198.18.0.0/15"),  # Network benchmark tests
    ipaddress.ip_network("::1/128"),        # IPv6 Loopback
    ipaddress.ip_network("fc00::/7"),       # IPv6 Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),      # IPv6 Link-Local
]


def is_ip_prohibited(ip_str: str) -> bool:
    """Check if an IP address falls within prohibited private, link-local, or metadata ranges."""
    try:
        ip_obj = ipaddress.ip_address(ip_str)
    except ValueError as err:
        raise SSRFSecurityError(f"Invalid IP address format: '{ip_str}'") from err

    if (
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_reserved
        or ip_obj.is_multicast
        or ip_obj.is_unspecified
    ):
        return True

    for net in DISALLOWED_NETWORKS:
        if ip_obj in net:
            return True

    return False


class SafeSSRFProtectionEngine:
    """Enforces zero-trust IP validation, pinned-IP dispatch, and redirect containment."""

    ALLOWED_SCHEMES: Set[str] = {"http", "https"}

    def __init__(
        self,
        max_redirects: int = 3,
        dns_resolver: Optional[Callable[[str, int], List[str]]] = None,
    ):
        self.max_redirects = max_redirects
        self._dns_resolver = dns_resolver or self._default_dns_resolve

    def _default_dns_resolve(self, hostname: str, port: int) -> List[str]:
        """Performs fresh DNS lookups returning resolved IP addresses."""
        try:
            addr_info = socket.getaddrinfo(hostname, port, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
            ips = [item[4][0] for item in addr_info if item[4]]
            if not ips:
                raise DNSResolutionError(f"No IP addresses found for hostname '{hostname}'")
            return list(dict.fromkeys(ips))
        except socket.gaierror as err:
            raise DNSResolutionError(f"Failed to resolve hostname '{hostname}': {err}") from err

    def validate_url(self, url: str) -> Tuple[str, str, int, str]:
        """Validates protocol scheme and extracts hostname, port, and path.

        Returns:
            Tuple of (scheme, hostname, port, path).
        """
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()

        if scheme not in self.ALLOWED_SCHEMES:
            raise InvalidSchemeError(
                f"Prohibited URL scheme '{scheme}'. Only HTTP and HTTPS are permitted."
            )

        hostname = parsed.hostname
        if not hostname:
            raise SSRFSecurityError("URL missing valid hostname")

        port = parsed.port or (443 if scheme == "https" else 80)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"

        return scheme, hostname, port, path

    def resolve_and_pin_ip(self, hostname: str, port: int) -> str:
        """Resolves hostname and verifies that NONE of the resolved addresses are private/metadata.

        Returns the validated, pinned IP to connect to directly, neutralizing DNS Rebinding TOCTOU.
        """
        # If hostname is already a raw literal IP
        try:
            ipaddress.ip_address(hostname)
            if is_ip_prohibited(hostname):
                raise PrivateIPAddressError(
                    f"SSRF violation: Direct target IP '{hostname}' belongs to prohibited network range"
                )
            return hostname
        except ValueError:
            pass  # Hostname is a domain name

        resolved_ips = self._dns_resolver(hostname, port)
        if not resolved_ips:
            raise DNSResolutionError(f"DNS lookup returned empty result for '{hostname}'")

        # Defense-in-depth: Every resolved A/AAAA record must pass the private/metadata filter
        for ip in resolved_ips:
            if is_ip_prohibited(ip):
                raise PrivateIPAddressError(
                    f"DNS Rebinding / SSRF blocked: Domain '{hostname}' resolved to prohibited IP '{ip}'"
                )

        # Pin to the first validated IP
        return resolved_ips[0]

    def build_safe_request_plan(
        self,
        target_url: str,
        current_redirect_count: int = 0,
    ) -> dict:
        """Prepares a safe execution plan by pinning the validated socket destination IP.

        Ensures that downstream HTTP dispatch connects to `pinned_ip` while preserving
        `Host: {hostname}` in the HTTP header.
        """
        if current_redirect_count > self.max_redirects:
            raise RedirectLimitExceededError(
                f"Redirect limit of {self.max_redirects} exceeded (attempted {current_redirect_count})"
            )

        scheme, hostname, port, path = self.validate_url(target_url)
        pinned_ip = self.resolve_and_pin_ip(hostname, port)

        return {
            "target_url": target_url,
            "scheme": scheme,
            "hostname": hostname,
            "port": port,
            "path": path,
            "pinned_ip": pinned_ip,
            "host_header": f"{hostname}:{port}" if (scheme == "http" and port != 80) or (scheme == "https" and port != 443) else hostname,
            "redirect_count": current_redirect_count,
        }

    def validate_redirect(
        self,
        current_url: str,
        redirect_location: str,
        current_redirect_count: int,
    ) -> dict:
        """Validates next hop during HTTP redirect handling, preventing redirection into internal metadata."""
        if current_redirect_count >= self.max_redirects:
            raise RedirectLimitExceededError(f"Maximum redirects ({self.max_redirects}) reached")

        next_url = urljoin(current_url, redirect_location)
        return self.build_safe_request_plan(next_url, current_redirect_count + 1)
