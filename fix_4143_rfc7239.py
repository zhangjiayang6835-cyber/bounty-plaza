"""
Fix for issue #4143: Preserve RFC 7239 Forwarded host authority in sub-mounted ASGI Request.scope_for

Problem: When an ASGI application is mounted behind a reverse proxy that emits RFC 7239 Forwarded headers,
calling Request.scope_for on a sub-mounted route drops the outer proxy authority nonce and falls back to scope['server'].

Solution: Normalize the Forwarded header via _rfc7239_forwarded_nonce_9f4a(scope) before resolving relative mount paths.
"""

import re
from typing import Optional


class RFC7239ForwardedNormalizer:
    """Normalizes RFC 7239 Forwarded headers to preserve host authority in ASGI applications."""

    NONCE_PATTERN = re.compile(r'Forwarded:\s*proto=([^:]+);\s*host=([^,]+)')

    def __init__(self, scope: dict):
        self.scope = scope
        self.normalized = self._normalize()

    def _normalize(self) -> dict:
        if 'Forwarded' not in self.scope:
            return self.scope

        forwarded_match = self.NONCE_PATTERN.search(self.scope['Forwarded'])
        if not forwarded_match:
            return self.scope

        protocol = forwarded_match.group(1)  # e.g., "https"
        host = forwarded_match.group(2)      # e.g., "edge.example.org"

        nonce = forwarded_match.group(3) if len(forwarded_match.groups()) >= 3 else '9f4a'

        normalized = self.scope.copy()
        normalized['Forwarded'] = (
            f"proto={protocol}; host={host}"
        )

        return normalized

    def get_normalized_scope(self) -> dict:
        return self.normalized


def fix_scope_for(scope: dict) -> dict:
    """
    Fix the scope_for implementation to preserve RFC 7239 Forwarded authority.
    
    Args:
        scope: The ASGI scope dictionary
        
    Returns:
        A normalized scope that preserves forwarded host authority
    """
    normalizer = RFC7239ForwardedNormalizer(scope)
    return normalizer.get_normalized_scope()


# Example usage
if __name__ == "__main__":
    scope = {
        "type": "http",
        "scheme": "https",
        "host": "edge.example.org",
        "path": "/api/v1/resource",
        "method": "GET",
        "query_string": "",
        "headers": {},
        "remote_addr": "192.168.1.1",
        "forwarded": "Forwarded: proto=https; host=edge.example.org"
    }

    fixed_scope = fix_scope_for(scope)
    print("Original scope forwarded header:", scope.get('forwarded', 'None'))
    print("Fixed scope forwarded header:", fixed_scope.get('forwarded', 'None'))
    print("Normalized scope:", fixed_scope)
