# fix_jwt_algo_confusion.py
import jwt
import json

class JWTAlgorithmProtection:
    """Protect against JWT algorithm confusion attacks (RS256→HS256 downgrade)."""

    # Only allow these algorithms
    ALLOWED_ALGORITHMS = {
        'RS256': {
            'type': 'asymmetric',
            'verify_key': 'public-key.pem',
        },
        'ES256': {
            'type': 'asymmetric',
            'verify_key': 'ec-public-key.pem',
        },
    }

    @classmethod
    def verify_token(cls, token):
        """
        Verify a JWT token with strict algorithm checking.
        Rejects any algorithm not in the whitelist.
        """
        # Decode header without verification to check alg
        header = jwt.get_unverified_header(token)
        alg = header.get('alg', 'none')

        # Reject 'none' algorithm
        if alg.lower() == 'none':
            raise ValueError("Algorithm 'none' is not allowed")

        # Check algorithm is in whitelist
        if alg not in cls.ALLOWED_ALGORITHMS:
            raise ValueError(f"Algorithm '{alg}' is not allowed")

        # Verify the algorithm matches what we expect
        expected_config = cls.ALLOWED_ALGORITHMS[alg]
        if expected_config['type'] == 'asymmetric':
            with open(expected_config['verify_key'], 'r') as f:
                public_key = f.read()
            # Use RS256 public key for verification
            payload = jwt.decode(
                token,
                public_key,
                algorithms=[alg],
                audience='api',
                issuer='auth-service',
            )
            return payload

        # For HMAC, use separate secrets
        if alg == 'HS256':
            raise ValueError("Algorithm 'HS256' is not allowed for this application")

        raise ValueError(f"Unsupported algorithm configuration: {alg}")

    @classmethod
    def get_unverified_claims(cls, token):
        """Get claims from token without verification (for debugging only)."""
        return jwt.decode(token, options={'verify_signature': False}, algorithms=list(cls.ALLOWED_ALGORITHMS.keys()))