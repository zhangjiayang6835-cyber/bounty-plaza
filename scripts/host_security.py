"""Host Header Validation & Password Reset URL Canonicalization.
Resolves Issue #80: Host Header Injection -> Password Reset Poisoning Defense ($120).
"""

from typing import List, Optional, Set
from urllib.parse import urlsplit, urlunsplit


class HostHeaderSecurityError(ValueError):
    """Raised when an untrusted or malformed Host header is detected."""
    pass


class HostSecurityManager:
    """Manages trusted host whitelisting, host normalization, and canonical URL generation."""

    def __init__(
        self,
        trusted_hosts: List[str],
        canonical_domain: Optional[str] = None,
        enforce_https: bool = True,
    ):
        """Initialize HostSecurityManager.

        Args:
            trusted_hosts: Whitelist of allowed domain names (e.g. ['bountyplaza.dev', 'app.bountyplaza.dev']).
            canonical_domain: Primary canonical domain to use for security-sensitive links (like password reset).
            enforce_https: If True, always generate https:// links.
        """
        if not trusted_hosts:
            raise HostHeaderSecurityError("Trusted hosts whitelist must not be empty.")

        self.trusted_hosts: Set[str] = {h.lower().strip() for h in trusted_hosts}
        self.canonical_domain = (canonical_domain or trusted_hosts[0]).lower().strip()
        self.enforce_https = enforce_https

        if self.canonical_domain not in self.trusted_hosts:
            self.trusted_hosts.add(self.canonical_domain)

    def normalize_host(self, host: Optional[str]) -> str:
        """Strip port and normalize host header.

        Args:
            host: Raw host string from HTTP header (e.g. 'evil.com', 'bountyplaza.dev:443').

        Returns:
            Normalized lowercase host without port.

        Raises:
            HostHeaderSecurityError: If host is empty or contains illegal characters.
        """
        if not host or not isinstance(host, str):
            raise HostHeaderSecurityError("Host header must be a non-empty string.")

        host_clean = host.strip().lower()
        if not host_clean:
            raise HostHeaderSecurityError("Host header cannot be blank.")

        # Disallow control characters or newline injection
        if any(c in host_clean for c in ("\r", "\n", "\t", " ", "@", "/", "\\")):
            raise HostHeaderSecurityError(f"Host header contains forbidden characters: {host_clean}")

        # If port is present, separate it
        if ":" in host_clean:
            host_clean = host_clean.split(":", 1)[0]

        return host_clean

    def is_host_trusted(self, host: Optional[str]) -> bool:
        """Verify whether an incoming Host header exists in the trusted whitelist."""
        try:
            norm = self.normalize_host(host)
            return norm in self.trusted_hosts
        except HostHeaderSecurityError:
            return False

    def validate_host_header(self, host: Optional[str]) -> str:
        """Validate that the incoming Host header is strictly whitelisted.

        Returns:
            Normalized trusted host name.

        Raises:
            HostHeaderSecurityError: If the host is not trusted.
        """
        norm = self.normalize_host(host)
        if norm not in self.trusted_hosts:
            raise HostHeaderSecurityError(
                f"Untrusted Host header '{norm}' rejected. Allowed hosts: {sorted(list(self.trusted_hosts))}"
            )
        return norm

    def generate_password_reset_url(
        self,
        token: str,
        incoming_host: Optional[str] = None,
        path: str = "/auth/reset-password",
    ) -> str:
        """Generate a tamper-proof absolute password reset URL.

        Even if an attacker provides a malicious Host header, this function strictly
        uses either the canonical configured domain or a validated whitelisted host,
        preventing phishing and password reset token poisoning.

        Args:
            token: Secure one-time password reset token.
            incoming_host: Optional incoming Host header from the current HTTP request.
            path: Relative reset path endpoint.

        Returns:
            Absolute canonical URL with HTTPS scheme.
        """
        if not token or not str(token).strip():
            raise ValueError("Reset token is required")

        # Prioritize canonical domain; if request host is provided, validate it strictly
        domain = self.canonical_domain
        if incoming_host:
            # Must pass whitelist validation or raise error
            validated = self.validate_host_header(incoming_host)
            # Use validated host or maintain strict canonical domain
            domain = validated

        scheme = "https" if self.enforce_https else "http"
        clean_path = path if path.startswith("/") else f"/{path}"
        query = f"token={token.strip()}"

        return urlunsplit((scheme, domain, clean_path, query, ""))
