# fix_jwt_kid_injection.py
import os
import re

class JWTKidProtection:
    """Protect against JWT Kid injection / path traversal attacks."""

    # Allowed key IDs mapped to their keys
    ALLOWED_KEYS = {
        'default-signing-key': 'default-secret-key-here',
        'v2-signing-key': 'v2-secret-key-here',
        'user-auth-key': 'user-auth-secret-key',
    }

    @classmethod
    def validate_kid(cls, kid):
        """
        Validate the kid (Key ID) header value.
        Returns True if the kid is safe, False otherwise.
        """
        if not kid or not isinstance(kid, str):
            return False

        # Reject path traversal
        if '..' in kid:
            return False

        # Reject absolute paths
        if kid.startswith('/') or kid.startswith('\\'):
            return False

        # Reject special characters
        if re.search(r'[<>:"|?*\x00-\x1f]', kid):
            return False

        # Must be in whitelist
        return kid in cls.ALLOWED_KEYS

    @classmethod
    def get_verification_key(cls, kid):
        """Get the verification key for a validated kid."""
        if cls.validate_kid(kid):
            return cls.ALLOWED_KEYS[kid]
        return None

    @classmethod
    def secure_verify(cls, token, kid):
        """Verify a JWT token with secure kid validation."""
        key = cls.get_verification_key(kid)
        if key is None:
            raise ValueError(f"Invalid or untrusted key ID: {kid}")
        return key