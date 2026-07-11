# fix_websocket_csrf.py
import re

class WebSocketCSRFProtection:
    """Protect WebSocket connections against CSRF attacks."""

    ALLOWED_ORIGINS = [
        'https://ai-research.example.com',
        'https://bounty-plaza.example.com',
        'http://localhost:8080',
        'http://localhost:5000',
        'http://127.0.0.1:8080',
        'http://127.0.0.1:5000',
    ]

    @classmethod
    def validate_origin(cls, origin):
        """Validate the Origin header for WebSocket connections."""
        if not origin:
            return False
        return origin in cls.ALLOWED_ORIGINS

    @classmethod
    def get_csrf_token_header(cls):
        """Return the CSRF token header name."""
        return 'X-CSRF-Token'

    @classmethod
    def validate_handshake(cls, headers):
        """
        Validate WebSocket handshake headers for CSRF protection.
        Returns (allowed, reason) tuple.
        """
        # Check Origin
        origin = headers.get('Origin', '')
        if not cls.validate_origin(origin):
            return False, "Invalid origin: %s" % origin

        # Check CSRF token in header
        csrf_token = headers.get(cls.get_csrf_token_header(), '')
        if not csrf_token or len(csrf_token) < 16:
            return False, "Missing or invalid CSRF token"

        # Check Sec-WebSocket-Protocol for token
        ws_protocol = headers.get('Sec-WebSocket-Protocol', '')
        if not ws_protocol:
            return False, "Missing Sec-WebSocket-Protocol header"

        return True, None

    @classmethod
    def get_secure_cookie_config(cls):
        """Return secure cookie configuration to prevent CSRF."""
        return {
            'SameSite': 'Strict',
            'Secure': True,
            'HttpOnly': True,
            'Domain': '.example.com',
        }

    @staticmethod
    def generate_csrf_token():
        """Generate a CSRF token for WebSocket authentication."""
        import secrets
        return secrets.token_hex(32)