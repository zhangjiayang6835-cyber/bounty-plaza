"""JWT Algorithm Confusion & Asymmetric/Symmetric Downgrade Defense.
Resolves Issue #62: JWT Algorithm Confusion (RS256 -> HS256 Downgrade) ($150).
"""

import base64
import json
import time
from typing import Any, Dict, List, Optional, Set, Tuple


class JWTError(Exception):
    """Base exception for JWT processing errors."""
    pass


class JWTAlgorithmConfusionError(JWTError):
    """Raised when the token header algorithm does not match the expected server algorithm."""
    pass


class JWTInvalidHeaderError(JWTError):
    """Raised when the JWT header is malformed, missing required fields, or forged."""
    pass


class JWTSignatureError(JWTError):
    """Raised when signature verification fails."""
    pass


class JWTExpiredError(JWTError):
    """Raised when token has expired."""
    pass


def base64url_decode(input_str: str) -> bytes:
    """Decode standard base64url string without padding."""
    rem = len(input_str) % 4
    if rem > 0:
        input_str += "=" * (4 - rem)
    return base64.urlsafe_b64decode(input_str.encode("utf-8"))


def base64url_encode(data: bytes) -> str:
    """Encode bytes into base64url string without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


class JWTValidator:
    """Secure JWT validator enforcing strict algorithm pinning and whitelist validation."""

    DEFAULT_ALLOWED_ALGORITHMS: Set[str] = {"RS256", "ES256", "EdDSA"}

    def __init__(
        self,
        allowed_algorithms: Optional[List[str]] = None,
        expected_algorithm: Optional[str] = "RS256",
        leeway_seconds: int = 60,
    ):
        """Initialize JWTValidator with explicit algorithm constraints.

        Args:
            allowed_algorithms: Set of permitted algorithm identifiers.
            expected_algorithm: Strict required algorithm for incoming tokens.
            leeway_seconds: Clock skew tolerance in seconds.
        """
        if allowed_algorithms is None:
            self.allowed_algorithms = set(self.DEFAULT_ALLOWED_ALGORITHMS)
        else:
            self.allowed_algorithms = set(allowed_algorithms)

        # Invariant: "none" algorithm is strictly forbidden
        if "none" in {a.lower() for a in self.allowed_algorithms}:
            raise JWTInvalidHeaderError("Insecure configuration: Algorithm 'none' is strictly prohibited.")

        self.expected_algorithm = expected_algorithm
        self.leeway_seconds = leeway_seconds

    def parse_header(self, token: str) -> Tuple[Dict[str, Any], str, str, str]:
        """Split token into parts and decode JSON header without verifying signature."""
        if not token or not isinstance(token, str):
            raise JWTInvalidHeaderError("Token must be a non-empty string")

        parts = token.strip().split(".")
        if len(parts) != 3:
            raise JWTInvalidHeaderError(f"Malformed JWT: Expected 3 segments, got {len(parts)}")

        header_b64, payload_b64, signature_b64 = parts

        try:
            header_bytes = base64url_decode(header_b64)
            header = json.loads(header_bytes.decode("utf-8"))
        except Exception as e:
            raise JWTInvalidHeaderError(f"Failed to parse JWT header: {str(e)}")

        if not isinstance(header, dict):
            raise JWTInvalidHeaderError("JWT header must be a JSON object")

        if "alg" not in header:
            raise JWTInvalidHeaderError("Missing required 'alg' header parameter")

        return header, header_b64, payload_b64, signature_b64

    def validate_algorithm(self, header: Dict[str, Any]) -> str:
        """Enforce strict algorithm pinning against whitelist and expected algorithm.

        Protects against RS256 -> HS256 algorithm confusion key misuse attacks.
        """
        alg = header.get("alg")
        if not isinstance(alg, str):
            raise JWTAlgorithmConfusionError("Algorithm parameter 'alg' must be a string")

        # Reject "none" or empty algorithm immediately
        if alg.lower() == "none" or not alg.strip():
            raise JWTAlgorithmConfusionError(f"Disallowed algorithm '{alg}': 'none' algorithm is rejected")

        # 1. Check against expected algorithm (pinning protects against confusion)
        if self.expected_algorithm and alg != self.expected_algorithm:
            raise JWTAlgorithmConfusionError(
                f"Algorithm confusion detected: Token uses '{alg}', but server strictly expects '{self.expected_algorithm}'"
            )

        # 2. Check against whitelist
        if alg not in self.allowed_algorithms:
            raise JWTAlgorithmConfusionError(
                f"Algorithm '{alg}' is not in the configured whitelist: {sorted(list(self.allowed_algorithms))}"
            )

        return alg

    def decode_and_verify(
        self,
        token: str,
        verify_signature_fn=None,
    ) -> Dict[str, Any]:
        """Decode and validate token payload ensuring algorithm authenticity.

        Args:
            token: Raw compact JWT string.
            verify_signature_fn: Optional callable (signing_input: bytes, signature: bytes, alg: str) -> bool.

        Returns:
            Decoded payload dictionary.
        """
        header, header_b64, payload_b64, signature_b64 = self.parse_header(token)

        # Validate algorithm BEFORE signature verification to abort downgrade attacks early
        alg = self.validate_algorithm(header)

        # Decode payload
        try:
            payload_bytes = base64url_decode(payload_b64)
            payload = json.loads(payload_bytes.decode("utf-8"))
        except Exception as e:
            raise JWTError(f"Failed to decode token payload: {str(e)}")

        if not isinstance(payload, dict):
            raise JWTError("Token payload must be a JSON object")

        # Verify signature if callback provided
        if verify_signature_fn is not None:
            signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
            signature_bytes = base64url_decode(signature_b64)
            if not verify_signature_fn(signing_input, signature_bytes, alg):
                raise JWTSignatureError(f"Signature verification failed for algorithm {alg}")

        # Check expiration (exp)
        if "exp" in payload:
            exp = payload["exp"]
            if isinstance(exp, (int, float)):
                now = time.time()
                if now > (exp + self.leeway_seconds):
                    raise JWTExpiredError(f"Token expired at {exp}, current time is {now}")

        return payload
