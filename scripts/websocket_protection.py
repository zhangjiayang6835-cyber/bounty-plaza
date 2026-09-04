"""WebSocket CSRF Protection & Handshake Origin Validator.
Resolves Issue #58: WebSocket CSRF -> Cross-Origin Data Exfiltration ($150).
"""

import hmac
import secrets
import time
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse


class WebSocketSecurityError(Exception):
    """Base exception for WebSocket security failures."""
    pass


class WebSocketOriginForbiddenError(WebSocketSecurityError):
    """Raised when the WebSocket Origin header is missing, untrusted, or null (HTTP 403)."""
    pass


class WebSocketCSRFValidationError(WebSocketSecurityError):
    """Raised when the handshake CSRF challenge token is invalid, expired, or missing (HTTP 403)."""
    pass


class WebSocketSecurityManager:
    """Manages WebSocket handshake origin whitelisting, CSRF ticket issuance, and ticket verification."""

    def __init__(
        self,
        allowed_origins: List[str],
        secret_key: Optional[str] = None,
        token_ttl_seconds: int = 60,
    ):
        """Initialize WebSocketSecurityManager.

        Args:
            allowed_origins: List of allowed origins (e.g. ['https://app.bountyplaza.dev']).
            secret_key: Secret key used to sign CSRF handshake tickets.
            token_ttl_seconds: Ticket expiration in seconds (default 60s).
        """
        if not allowed_origins:
            raise ValueError("Allowed origins whitelist must not be empty")

        self.allowed_origins: Set[str] = set()
        for o in allowed_origins:
            clean = o.strip().rstrip("/")
            if clean:
                self.allowed_origins.add(clean)

        self.secret_key = (secret_key or secrets.token_hex(32)).encode("utf-8")
        self.token_ttl_seconds = token_ttl_seconds

    def validate_origin(self, origin: Optional[str]) -> bool:
        """Validate the incoming handshake Origin header against the strict whitelist.

        Rejects null, empty, wildcard, or unknown origins.
        """
        if not origin or not isinstance(origin, str):
            return False

        clean_origin = origin.strip().rstrip("/")
        if not clean_origin or clean_origin == "null":
            return False

        if clean_origin in self.allowed_origins:
            return True

        # Normalized URL match
        try:
            parsed = urlparse(clean_origin)
            if not parsed.scheme or not parsed.netloc:
                return False
            normalized = f"{parsed.scheme}://{parsed.netloc}"
            return normalized in self.allowed_origins
        except Exception:
            return False

    def generate_csrf_ticket(self, session_id: str) -> str:
        """Issue a signed, short-lived one-time CSRF challenge token tied to the user's session.

        Format: session_id:timestamp:nonce:signature
        """
        if not session_id or not str(session_id).strip():
            raise ValueError("session_id is required to issue CSRF ticket")

        now = f"{time.time():.4f}"
        nonce = secrets.token_hex(16)
        payload = f"{session_id}:{now}:{nonce}"
        signature = hmac.new(self.secret_key, payload.encode("utf-8"), "sha256").hexdigest()
        return f"{payload}:{signature}"

    def verify_csrf_ticket(self, ticket: Optional[str], session_id: str) -> bool:
        """Verify the cryptographic authenticity and expiration of a CSRF ticket."""
        if not ticket or not isinstance(ticket, str):
            return False

        parts = ticket.strip().split(":")
        if len(parts) != 4:
            return False

        tok_session, tok_time_str, tok_nonce, tok_sig = parts

        if tok_session != session_id:
            return False

        try:
            tok_time = float(tok_time_str)
        except ValueError:
            return False

        # Check expiration
        now = time.time()
        if (now - tok_time) > self.token_ttl_seconds or tok_time > (now + 5.0):
            return False

        expected_payload = f"{tok_session}:{tok_time_str}:{tok_nonce}"
        expected_sig = hmac.new(self.secret_key, expected_payload.encode("utf-8"), "sha256").hexdigest()

        return hmac.compare_digest(expected_sig, tok_sig)

    def authorize_handshake(
        self,
        headers: Dict[str, str],
        session_id: str,
        csrf_ticket: Optional[str] = None
    ) -> Tuple[int, str]:
        """Authorize an incoming WebSocket upgrade handshake.

        Returns:
            Tuple[status_code, status_message] -> (101, "Switching Protocols") or (403, "Forbidden")

        Raises:
            WebSocketOriginForbiddenError: If Origin header fails whitelist.
            WebSocketCSRFValidationError: If CSRF ticket verification fails.
        """
        # Case-insensitive header lookup
        header_map = {k.lower(): v for k, v in headers.items()}
        origin = header_map.get("origin")

        # 1. Validate Origin
        if not self.validate_origin(origin):
            raise WebSocketOriginForbiddenError(
                f"Handshake rejected: Origin '{origin}' is not authorized. HTTP 403 Forbidden."
            )

        # 2. Validate CSRF challenge ticket
        ticket = csrf_ticket or header_map.get("x-csrf-token") or header_map.get("sec-websocket-protocol")
        if not self.verify_csrf_ticket(ticket, session_id):
            raise WebSocketCSRFValidationError(
                "Handshake rejected: Missing or invalid CSRF challenge token. HTTP 403 Forbidden."
            )

        return 101, "Switching Protocols"
