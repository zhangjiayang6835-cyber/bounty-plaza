# fix_web_cache_deception.py
from flask import request, Response

class CacheDeceptionProtection:
    """Middleware to protect against web cache deception attacks."""

    SENSITIVE_PATHS = [
        '/account',
        '/profile',
        '/settings',
        '/dashboard',
        '/api/',
        '/transfer',
        '/withdraw',
    ]

    @classmethod
    def should_no_cache(cls, path):
        """Check if the path should never be cached."""
        for sensitive in cls.SENSITIVE_PATHS:
            if path.startswith(sensitive):
                return True
        return False

    @classmethod
    def get_cache_headers(cls, path):
        """Return appropriate cache headers based on the path."""
        if cls.should_no_cache(path):
            return {
                'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0',
                'X-Content-Type-Options': 'nosniff',
            }
        return {
            'X-Content-Type-Options': 'nosniff',
            'Vary': 'Accept-Encoding',
        }

    @classmethod
    def is_cache_deception_request(cls, path):
        """Detect potential cache deception attempts."""
        # Check if the path has a static file extension but is actually dynamic
        static_extensions = ['.css', '.js', '.png', '.jpg', '.gif', '.ico', '.svg']
        for ext in static_extensions:
            if path.endswith(ext) and cls.should_no_cache(path[:-len(ext)]):
                return True
        return False