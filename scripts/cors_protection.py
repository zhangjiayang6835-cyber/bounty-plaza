"""CORS Security Middleware & Origin Whitelist Validator.
Resolves Issue #295: CORS Misconfiguration + Origin Reflection Defense.
"""

from typing import Dict, List, Optional, Set
from urllib.parse import urlparse


class CORSValidationError(Exception):
    """Raised when CORS configuration violates security policies."""
    pass


class CORSSecurityManager:
    """Manages CORS origin validation, credential handling, and response headers."""

    def __init__(
        self,
        allowed_origins: Optional[List[str]] = None,
        allow_credentials: bool = False,
        allowed_methods: Optional[List[str]] = None,
        allowed_headers: Optional[List[str]] = None,
        max_age: int = 86400,
    ):
        self.allowed_origins: Set[str] = set(allowed_origins or [])
        self.allow_credentials: bool = allow_credentials
        self.allowed_methods: List[str] = allowed_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allowed_headers: List[str] = allowed_headers or ["Content-Type", "Authorization", "X-Requested-With"]
        self.max_age: int = max_age

        # Enforce invariant: Wildcard origin cannot be used with credentials
        if self.allow_credentials and "*" in self.allowed_origins:
            raise CORSValidationError(
                "Insecure CORS configuration: Wildcard '*' origin is forbidden when 'allow_credentials' is True."
            )

    def is_origin_allowed(self, origin: Optional[str]) -> bool:
        """Check if an incoming origin is strictly authorized by whitelist.
        Disallows dynamic reflection of untrusted origins and null origins.
        """
        if not origin:
            return False

        origin = origin.strip()
        if origin == "null" and "null" not in self.allowed_origins:
            return False

        if "*" in self.allowed_origins and not self.allow_credentials:
            return True

        # Exact match check
        if origin in self.allowed_origins:
            return True

        # Normalized URL match (scheme + host + port)
        try:
            parsed = urlparse(origin)
            if not parsed.scheme or not parsed.netloc:
                return False
            normalized = f"{parsed.scheme}://{parsed.netloc}"
            return normalized in self.allowed_origins
        except Exception:
            return False

    def build_cors_headers(
        self,
        origin: Optional[str],
        is_preflight: bool = False
    ) -> Dict[str, str]:
        """Generate safe, standards-compliant CORS headers.
        Always emits 'Vary: Origin' to prevent upstream caching poisoning.
        """
        headers: Dict[str, str] = {
            "Vary": "Origin"
        }

        if not origin or not self.is_origin_allowed(origin):
            # Origin is not whitelisted: do not emit Access-Control-Allow-Origin
            return headers

        # Valid whitelisted origin
        if "*" in self.allowed_origins and not self.allow_credentials:
            headers["Access-Control-Allow-Origin"] = "*"
        else:
            headers["Access-Control-Allow-Origin"] = origin

        if self.allow_credentials:
            headers["Access-Control-Allow-Credentials"] = "true"

        if is_preflight:
            headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
            headers["Access-Control-Allow-Headers"] = ", ".join(self.allowed_headers)
            headers["Access-Control-Max-Age"] = str(self.max_age)

        return headers
