"""Secure OAuth 2.0 helpers: state nonce validation, session binding, and PKCE.

Fixes the OAuth 2.0 CSRF / account-takeover issue by ensuring:
  1. The ``state`` parameter is a cryptographically random, single-use nonce.
  2. The ``state`` value is bound to the user's session, so a state generated
     in one session cannot be replayed in another (blocks login CSRF).
  3. PKCE (RFC 7636, S256) is used on every authorization request.
"""

import base64
import hashlib
import hmac
import secrets
import time
from urllib.parse import urlencode

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"

# A state is valid for 10 minutes and can only be used once.
STATE_TTL_SECONDS = 600


class OAuthStateError(Exception):
    """Raised when the OAuth ``state`` parameter fails validation."""


def _generate_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def derive_code_challenge(code_verifier: str) -> str:
    """Derive the S256 code_challenge from a code_verifier (RFC 7636)."""
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class OAuthStateManager:
    """Server-side store mapping state nonces to sessions and PKCE verifiers.

    The store is intentionally simple (in-memory dict) so it can be swapped
    for Redis/DB in a multi-process deployment without changing the API.
    """

    def __init__(self, ttl_seconds: int = STATE_TTL_SECONDS):
        self._ttl = ttl_seconds
        self._store = {}

    def create_authorization_request(
        self,
        session_id: str,
        client_id: str,
        redirect_uri: str,
        scope: str = "read:user",
    ):
        """Start an authorization request for ``session_id``.

        Returns ``(authorization_url, state)``. The PKCE ``code_verifier`` is
        kept server-side and handed back only when the callback validates.
        """
        if not session_id:
            raise ValueError("session_id is required to bind the OAuth state")

        state = _generate_token(32)
        code_verifier = _generate_token(48)

        self._store[state] = {
            "session_id": session_id,
            "code_verifier": code_verifier,
            "expires_at": time.time() + self._ttl,
        }

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
            # PKCE extension
            "code_challenge": derive_code_challenge(code_verifier),
            "code_challenge_method": "S256",
            "response_type": "code",
        }
        url = f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"
        return url, state

    def validate_callback(self, session_id: str, state: str) -> str:
        """Validate the ``state`` returned by the provider.

        Checks, in order: presence, existence (single-use — the entry is
        consumed on lookup), session binding (constant-time compare), and
        expiry. Returns the PKCE ``code_verifier`` for the token exchange.

        Raises :class:`OAuthStateError` on any failure.
        """
        if not state:
            raise OAuthStateError("missing state parameter")

        # pop() guarantees single use: a replayed state is already gone.
        entry = self._store.pop(state, None)
        if entry is None:
            raise OAuthStateError("unknown or already-used state")

        if not hmac.compare_digest(
            str(entry["session_id"]).encode("utf-8"),
            str(session_id or "").encode("utf-8"),
        ):
            raise OAuthStateError("state does not match the user session")

        if time.time() > entry["expires_at"]:
            raise OAuthStateError("state has expired")

        return entry["code_verifier"]
