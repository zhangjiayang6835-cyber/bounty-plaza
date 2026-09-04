"""OAuth 2.0 CSRF Defense, Session-Bound State & PKCE Engine.
Resolves Issue #296: OAuth 2.0 CSRF -> Account Takeover via State Bypass ($150).
Compliant with RFC 6749 Section 10.12 and RFC 7636 (PKCE).
Enforces session-bound cryptographic state nonces and SHA-256 PKCE code challenges.
"""

import base64
import hashlib
import hmac
import secrets
import time
from typing import Any, Dict, Optional, Tuple


class OAuthSecurityError(ValueError):
    """Base exception for OAuth security violations."""
    pass


class InvalidOAuthStateError(OAuthSecurityError):
    """Raised when the OAuth 'state' parameter is missing, expired, or not bound to session."""
    pass


class PKCEValidationError(OAuthSecurityError):
    """Raised when the PKCE code_verifier does not match code_challenge."""
    pass


def base64url_encode(data: bytes) -> str:
    """Encode bytes into RFC 7636 base64url string without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def generate_code_verifier(length: int = 64) -> str:
    """Generate a high-entropy cryptographically random PKCE code_verifier (RFC 7636 §4.1).

    Args:
        length: Length between 43 and 128 characters.
    """
    if not (43 <= length <= 128):
        raise ValueError("PKCE code_verifier length must be between 43 and 128 characters")
    raw = secrets.token_urlsafe(length)
    return raw[:length]


def compute_code_challenge_s256(verifier: str) -> str:
    """Compute S256 code_challenge from code_verifier (RFC 7636 §4.2):
    code_challenge = BASE64URL-ENCODE(SHA256(ASCII(code_verifier)))
    """
    if not (43 <= len(verifier) <= 128):
        raise PKCEValidationError("Invalid code_verifier length")
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64url_encode(digest)


class OAuthSecurityManager:
    """Manages secure authorization request generation and callback verification.
    Guarantees session binding for state nonces and enforces PKCE verification.
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        state_ttl_seconds: int = 300,
    ):
        self.secret_key = (secret_key or secrets.token_hex(32)).encode("utf-8")
        self.state_ttl_seconds = state_ttl_seconds
        # In-memory session auth flow tracking: session_id -> {nonce, code_challenge, created_at}
        self._pending_flows: Dict[str, Dict[str, Any]] = {}

    def create_authorization_request(
        self,
        session_id: str,
        client_id: str,
        redirect_uri: str,
        scope: str = "read:user",
    ) -> Tuple[str, str, str]:
        """Generate parameters for OAuth authorization redirect with state and PKCE.

        Args:
            session_id: Authenticated user's browser session ID.
            client_id: OAuth client ID.
            redirect_uri: Whitelisted callback URL.
            scope: Requested OAuth scopes.

        Returns:
            Tuple of (authorization_url_query_params, state_token, code_verifier).
        """
        if not session_id or not session_id.strip():
            raise ValueError("session_id is required to bind OAuth state")

        now = time.time()
        nonce = secrets.token_hex(16)
        payload = f"{session_id}:{now:.4f}:{nonce}"
        sig = hmac.new(self.secret_key, payload.encode("utf-8"), "sha256").hexdigest()
        state = f"{payload}:{sig}"

        verifier = generate_code_verifier(64)
        challenge = compute_code_challenge_s256(verifier)

        # Record state and challenge bound to session_id
        self._pending_flows[session_id] = {
            "nonce": nonce,
            "created_at": now,
            "code_challenge": challenge,
            "redirect_uri": redirect_uri,
        }

        query = (
            f"client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope={scope}"
            f"&state={state}"
            f"&code_challenge={challenge}"
            f"&code_challenge_method=S256"
        )
        return query, state, verifier

    def verify_callback_state(
        self,
        received_state: Optional[str],
        session_id: str,
    ) -> bool:
        """Verify that the callback state matches the user's session and has not expired."""
        if not received_state or not isinstance(received_state, str):
            raise InvalidOAuthStateError("Missing 'state' parameter in OAuth callback. CSRF blocked.")

        parts = received_state.strip().split(":")
        if len(parts) != 4:
            raise InvalidOAuthStateError("Malformed OAuth state token format")

        tok_session, tok_time_str, tok_nonce, tok_sig = parts

        # Strict session binding check
        if tok_session != session_id:
            raise InvalidOAuthStateError(
                f"OAuth CSRF Attack Detected: State is bound to session '{tok_session}', "
                f"which does not match current session '{session_id}'."
            )

        try:
            tok_time = float(tok_time_str)
        except ValueError:
            raise InvalidOAuthStateError("Invalid timestamp in OAuth state")

        now = time.time()
        if now - tok_time > self.state_ttl_seconds or tok_time > now + 5.0:
            raise InvalidOAuthStateError("OAuth state parameter has expired")

        expected_payload = f"{tok_session}:{tok_time_str}:{tok_nonce}"
        expected_sig = hmac.new(self.secret_key, expected_payload.encode("utf-8"), "sha256").hexdigest()

        if not hmac.compare_digest(expected_sig, tok_sig):
            raise InvalidOAuthStateError("OAuth state signature verification failed: forged state token")

        # Verify flow exists in storage
        flow = self._pending_flows.get(session_id)
        if not flow or flow.get("nonce") != tok_nonce:
            raise InvalidOAuthStateError("No pending OAuth authorization flow for this state token")

        return True

    def verify_pkce(
        self,
        session_id: str,
        code_verifier: str,
    ) -> bool:
        """Validate PKCE code_verifier against stored code_challenge for the session."""
        flow = self._pending_flows.get(session_id)
        if not flow:
            raise PKCEValidationError("No pending OAuth flow found for session")

        expected_challenge = flow.get("code_challenge")
        computed_challenge = compute_code_challenge_s256(code_verifier)

        if not hmac.compare_digest(expected_challenge, computed_challenge):
            raise PKCEValidationError("PKCE verification failed: code_verifier does not match code_challenge")

        # Clean up completed flow
        self._pending_flows.pop(session_id, None)
        return True
