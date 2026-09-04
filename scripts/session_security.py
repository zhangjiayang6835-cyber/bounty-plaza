"""Session Fixation & URL Session Leakage Defense.
Resolves Issue #76: Session Fixation + Session ID in URL Defense ($120).
"""

import secrets
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlsplit


class SessionSecurityError(ValueError):
    """Raised when session security constraints are violated."""
    pass


class SessionManager:
    """Secure Session Manager enforcing cookie-only transport, post-auth regeneration,
    and Secure + HttpOnly + SameSite cookie attributes.
    """

    def __init__(
        self,
        cookie_name: str = "__Host-sessionid",
        session_ttl_seconds: int = 3600,
        enforce_secure_cookie: bool = True,
        same_site: str = "Strict",
    ):
        self.cookie_name = cookie_name
        self.session_ttl_seconds = session_ttl_seconds
        self.enforce_secure_cookie = enforce_secure_cookie
        self.same_site = same_site
        # In-memory storage: session_id -> {data: dict, created_at: float, expires_at: float}
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def _generate_session_id(self) -> str:
        """Generate high-entropy cryptographically random session ID."""
        return secrets.token_urlsafe(32)

    def extract_session_id(
        self,
        request_url: str,
        cookie_header: Optional[str] = None
    ) -> Optional[str]:
        """Extract session ID strictly from Cookies while rejecting URL parameter leakage.

        Args:
            request_url: Full incoming request URL or query string.
            cookie_header: Raw Cookie header string.

        Returns:
            Extracted session_id if found in cookie, or None.

        Raises:
            SessionSecurityError: If session id is detected in URL parameters.
        """
        # 1. Audit URL query parameters for session fixation attempt
        parsed = urlsplit(request_url)
        query_params = parse_qs(parsed.query, keep_blank_values=True)
        dangerous_params = {"sessionid", "session_id", "sid", "jsessionid", "phpsessid"}

        for param in dangerous_params:
            if param in query_params:
                raise SessionSecurityError(
                    f"Session Fixation Attempt Blocked: Session identifiers in URL parameters ('{param}') are strictly prohibited."
                )

        # 2. Extract strictly from Cookie header
        if not cookie_header:
            return None

        cookies: Dict[str, str] = {}
        for item in cookie_header.split(";"):
            item = item.strip()
            if not item:
                continue
            if "=" in item:
                k, v = item.split("=", 1)
                cookies[k.strip()] = v.strip()

        return cookies.get(self.cookie_name)

    def create_session(self, initial_data: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
        """Create a new unauthenticated or guest session.

        Returns:
            Tuple of (session_id, set_cookie_header_string).
        """
        sid = self._generate_session_id()
        now = time.time()
        self.sessions[sid] = {
            "data": dict(initial_data or {}),
            "created_at": now,
            "expires_at": now + self.session_ttl_seconds,
            "authenticated": False,
        }
        cookie_header = self.build_set_cookie_header(sid)
        return sid, cookie_header

    def regenerate_session(
        self,
        old_session_id: Optional[str],
        authenticated_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """Regenerate session ID upon successful authentication to eliminate session fixation.

        Destroys old session and issues fresh cryptographic identifier while preserving user data.

        Args:
            old_session_id: Prior session token held before login.
            authenticated_data: User authentication payload (user_id, role, etc.).

        Returns:
            Tuple of (new_session_id, set_cookie_header_string).
        """
        migrated_data: Dict[str, Any] = {}

        if old_session_id and old_session_id in self.sessions:
            # Copy existing session data and invalidate previous session ID
            old_record = self.sessions.pop(old_session_id)
            migrated_data = old_record.get("data", {})

        if authenticated_data:
            migrated_data.update(authenticated_data)

        # Generate fresh session ID
        new_sid = self._generate_session_id()
        now = time.time()
        self.sessions[new_sid] = {
            "data": migrated_data,
            "created_at": now,
            "expires_at": now + self.session_ttl_seconds,
            "authenticated": True,
        }

        cookie_header = self.build_set_cookie_header(new_sid)
        return new_sid, cookie_header

    def get_session_data(self, session_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Retrieve and validate session data checking TTL expiration."""
        if not session_id or session_id not in self.sessions:
            return None

        record = self.sessions[session_id]
        if time.time() > record["expires_at"]:
            # Expired session cleanup
            self.sessions.pop(session_id, None)
            return None

        return record["data"]

    def build_set_cookie_header(
        self,
        session_id: str,
        max_age: Optional[int] = None
    ) -> str:
        """Construct RFC 6265 compliant Set-Cookie header with Secure, HttpOnly, and SameSite."""
        ttl = max_age if max_age is not None else self.session_ttl_seconds
        parts = [
            f"{self.cookie_name}={session_id}",
            "Path=/",
            f"Max-Age={ttl}",
            "HttpOnly",
            f"SameSite={self.same_site}",
        ]
        if self.enforce_secure_cookie:
            parts.append("Secure")

        return "; ".join(parts)
