# fix_cache_poisoning.py
import hashlib
from flask import request

class CachePoisoningProtection:
    """Protect against web cache poisoning via unkeyed headers."""

    # Headers that should be part of the cache key
    CACHE_KEY_HEADERS = [
        'Host',
        'X-Forwarded-Host',
        'X-Forwarded-Proto',
        'X-Original-URL',
        'X-Rewrite-URL',
        'Accept',
        'Accept-Encoding',
        'Accept-Language',
    ]

    # Headers that should be validated/sanitized
    DANGEROUS_HEADERS = [
        'X-Forwarded-Host',
        'X-Original-URL',
        'X-Rewrite-URL',
        'X-Forwarded-Scheme',
    ]

    @classmethod
    def get_cache_key(cls, path):
        """Generate a secure cache key including security-relevant headers."""
        components = [path]
        for header in cls.CACHE_KEY_HEADERS:
            value = request.headers.get(header, '')
            if value:
                components.append(f'{header}:{value}')
        return hashlib.sha256('|'.join(components).encode()).hexdigest()

    @classmethod
    def validate_headers(cls):
        """Validate that dangerous headers contain safe values."""
        for header in cls.DANGEROUS_HEADERS:
            value = request.headers.get(header)
            if value:
                # Reject URLs with path traversal or special characters
                if '..' in value or '\\' in value:
                    return False
        return True

    @classmethod
    def get_vary_headers(cls):
        """Return Vary header values for cache-aware responses."""
        return ', '.join(cls.CACHE_KEY_HEADERS)