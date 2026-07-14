# fix_oauth2_csrf.py
import secrets
import hashlib
import base64

class OAuth2CSRFProtection:
    """Protect against OAuth 2.0 CSRF attacks via state parameter and PKCE."""

    # Allowed redirect URIs - whitelist only
    ALLOWED_REDIRECT_URIS = [
        'https://example.com/oauth/callback',
        'https://app.example.com/oauth/callback',
        'http://localhost:8080/oauth/callback',
    ]

    @classmethod
    def generate_state_token(cls):
        """Generate a CSRF-safe state token for OAuth."""
        return secrets.token_hex(32)

    @classmethod
    def generate_pkce_challenge(cls):
        """Generate PKCE code verifier and challenge."""
        verifier = secrets.token_urlsafe(64)
        # Create S256 challenge
        challenge = hashlib.sha256(verifier.encode()).digest()
        challenge_b64 = base64.urlsafe_b64encode(challenge).rstrip(b'=').decode()
        return verifier, challenge_b64

    @classmethod
    def validate_callback(cls, state, code, redirect_uri, stored_state, code_verifier=None):
        """
        Validate OAuth 2.0 callback parameters.
        Returns (valid, error) tuple.
        """
        # Validate state parameter
        if not state or not stored_state:
            return False, "Missing state parameter"

        if state != stored_state:
            return False, "State mismatch - possible CSRF attack"

        # Validate redirect URI
        if redirect_uri not in cls.ALLOWED_REDIRECT_URIS:
            return False, "Invalid redirect URI"

        # Validate PKCE code verifier if provided
        if code_verifier:
            if len(code_verifier) < 43 or len(code_verifier) > 128:
                return False, "Invalid code verifier length"

        return True, None

    @classmethod
    def build_auth_url(cls, state, redirect_uri, code_challenge=None):
        """Build a secure OAuth 2.0 authorization URL."""
        if redirect_uri not in cls.ALLOWED_REDIRECT_URIS:
            raise ValueError("Invalid redirect URI")

        base = "https://auth.example.com/oauth/authorize"
        params = {
            'client_id': 'your-client-id',
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'openid profile email',
            'state': state,
        }

        if code_challenge:
            params['code_challenge'] = code_challenge
            params['code_challenge_method'] = 'S256'

        # Build URL with parameters
        query = '&'.join('%s=%s' % (k, v) for k, v in params.items())
        return "%s?%s" % (base, query)

    @classmethod
    def store_oauth_session(cls, state, redirect_uri, code_verifier):
        """Store OAuth session data for validation."""
        import datetime
        return {
            'state': state,
            'redirect_uri': redirect_uri,
            'code_verifier': code_verifier,
            'created_at': datetime.datetime.utcnow().isoformat(),
            'expires_at': (datetime.datetime.utcnow() + datetime.timedelta(minutes=10)).isoformat(),
        }