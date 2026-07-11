# fix_grpc_reflection.py
"""
gRPC Reflection Protection - Disable reflection service in production.

gRPC reflection service allows clients to discover available services, methods,
and schemas. In production, this should be disabled to prevent service enumeration.

Secure configuration:
```python
import grpc
from grpc_reflection.v1alpha import reflection

# Disable reflection in production
ENFORCE_NO_REFLECTION = True  # Set to False only for development

def create_secure_server(services, reflection_enabled=False):
    server = grpc.server(thread_pool)
    # Register user services
    for service in services:
        service.register_server(server)

    # Only enable reflection for development/staging
    if reflection_enabled and not ENFORCE_NO_REFLECTION:
        reflection.enable_reflection(server, services)
        print("WARNING: gRPC reflection is enabled - do not use in production")
    else:
        print("gRPC reflection is disabled for security")

    return server
```
"""

class gRPCReflectionProtection:
    """Protect against service enumeration via gRPC reflection."""

    # Production flag - reflection should be disabled
    PRODUCTION = True

    @classmethod
    def should_enable_reflection(cls):
        """Check if gRPC reflection should be enabled."""
        if cls.PRODUCTION:
            return False
        # Only enable in development/staging
        return False  # Always False in this secure config

    @classmethod
    def create_secure_server(cls, services, reflection_enabled=None):
        """
        Create a gRPC server with reflection disabled by default.
        Override reflection_enabled explicitly to enable in dev.
        """
        import grpc

        # Always disable reflection in production
        if cls.PRODUCTION and reflection_enabled:
            print("WARNING: gRPC reflection disabled in production despite override")
            reflection_enabled = False

        server = grpc.server(grpc.thread_pool_max_workers(10))
        for service in services:
            service.register_server(server)

        return server

    @staticmethod
    def check_reflection_request(channel):
        """Check if incoming request is a reflection request."""
        # Block reflection service calls
        reflection_methods = [
            '/grpc.reflection.v1alpha.reflection/ServerReflectionInfo',
        ]
        method = channel._method if hasattr(channel, '_method') else ''
        if method in reflection_methods:
            raise RuntimeError("gRPC reflection is disabled")

    @staticmethod
    def get_reflection_security_config():
        """Return security configuration for gRPC reflection."""
        return {
            'reflection_enabled': False,
            'allowed_reflection_clients': [],
            'log_reflection_attempts': True,
            'require_authentication': True,
        }