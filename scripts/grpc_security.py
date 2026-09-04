"""gRPC Reflection Policy & Service-to-Service Authentication Engine.
Resolves Issue #180: gRPC Reflection Enabled -> Service Enumeration Defense ($120).
Enforces reflection disabling in production, mTLS verification, and Bearer service token authentication.
"""

import hmac
import os
from typing import Any, Dict, List, Optional, Set, Tuple


class GRPCStatus:
    OK = 0
    PERMISSION_DENIED = 7
    UNAUTHENTICATED = 16
    UNIMPLEMENTED = 12


class GRPCSecurityError(Exception):
    """Base exception for gRPC interception errors."""
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class GRPCSecurityInterceptor:
    """Interceps gRPC incoming calls to enforce authentication and reflection policy."""

    REFLECTION_SERVICE_NAME = "grpc.reflection.v1alpha.ServerReflection"

    def __init__(
        self,
        environment: str = "production",
        allowed_service_tokens: Optional[Dict[str, str]] = None,
        require_mtls: bool = True,
        allowed_client_common_names: Optional[List[str]] = None,
    ):
        """Initialize GRPCSecurityInterceptor.

        Args:
            environment: Environment name ('production', 'staging', 'development').
            allowed_service_tokens: Dict mapping service_name -> expected_token.
            require_mtls: Whether client TLS certificate verification is enforced.
            allowed_client_common_names: Whitelist of allowed mTLS client Common Names (CN).
        """
        self.environment = environment.lower().strip()
        self.allowed_service_tokens = allowed_service_tokens or {}
        self.require_mtls = require_mtls
        self.allowed_client_common_names = set(allowed_client_common_names or [])

        # Invariant: ServerReflection must NEVER be enabled in production or staging
        self.reflection_enabled = self.environment not in ("production", "staging", "prod")

    def intercept_call(
        self,
        service_name: str,
        method_name: str,
        metadata: Dict[str, str],
        client_cert_info: Optional[Dict[str, Any]] = None,
    ) -> Tuple[int, str]:
        """Validate an incoming gRPC call across reflection rules, mTLS, and service tokens.

        Args:
            service_name: gRPC service name.
            method_name: Method invoked.
            metadata: Incoming gRPC headers/metadata dictionary.
            client_cert_info: Parsed client certificate if present (e.g. {'cn': 'payments-svc', 'verified': True}).

        Returns:
            Tuple of (GRPCStatus code, diagnostic message).

        Raises:
            GRPCSecurityError: On reflection block, unauthenticated token, or mTLS failure.
        """
        clean_service = (service_name or "").strip()

        # 1. Guard against ServerReflection service enumeration in production
        if clean_service == self.REFLECTION_SERVICE_NAME or "ServerReflection" in clean_service:
            if not self.reflection_enabled:
                raise GRPCSecurityError(
                    GRPCStatus.UNIMPLEMENTED,
                    f"gRPC Reflection API is strictly disabled in {self.environment} environment."
                )

        # 2. Enforce mutual TLS (mTLS) client certificate verification
        if self.require_mtls:
            if not client_cert_info or not client_cert_info.get("verified", False):
                raise GRPCSecurityError(
                    GRPCStatus.UNAUTHENTICATED,
                    "Mutual TLS (mTLS) handshake required: Client certificate missing or unverified."
                )

            client_cn = client_cert_info.get("cn")
            if self.allowed_client_common_names and client_cn not in self.allowed_client_common_names:
                raise GRPCSecurityError(
                    GRPCStatus.PERMISSION_DENIED,
                    f"Client certificate Common Name '{client_cn}' is not authorized."
                )

        # 3. Enforce internal API service token authentication
        if self.allowed_service_tokens:
            meta_map = {k.lower(): v for k, v in metadata.items()}
            auth_header = meta_map.get("authorization", "") or meta_map.get("x-service-token", "")

            token = ""
            if auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()
            else:
                token = auth_header.strip()

            if not token:
                raise GRPCSecurityError(
                    GRPCStatus.UNAUTHENTICATED,
                    "Service authentication required: Missing 'authorization' or 'x-service-token' metadata."
                )

            # Check if token matches any registered service token using constant-time comparison
            token_valid = False
            for svc_name, valid_secret in self.allowed_service_tokens.items():
                if hmac.compare_digest(token, valid_secret):
                    token_valid = True
                    break

            if not token_valid:
                raise GRPCSecurityError(
                    GRPCStatus.PERMISSION_DENIED,
                    "Service authentication failed: Invalid service token."
                )

        return GRPCStatus.OK, "Authorized"
