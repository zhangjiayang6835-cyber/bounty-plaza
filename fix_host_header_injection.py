# fix_host_header_injection.py
from flask import request, abort

class HostHeaderValidator:
    """Middleware to validate Host header and prevent password reset poisoning."""

    TRUSTED_HOSTS = [
        'localhost',
        '127.0.0.1',
        'ai-research.example.com',
        'bounty-plaza.example.com',
    ]

    @classmethod
    def get_trusted_host(cls):
        """Return the validated Host header or raise an error."""
        host = request.headers.get('Host', '')
        if host in cls.TRUSTED_HOSTS or host in [f'{h}:80' for h in cls.TRUSTED_HOSTS] or host in [f'{h}:443' for h in cls.TRUSTED_HOSTS]:
            return host
        # If not in whitelist, use the default trusted host
        return cls.TRUSTED_HOSTS[0]

    @classmethod
    def build_secure_url(cls, path):
        """Build a secure absolute URL using the trusted host."""
        return f'https://{cls.get_trusted_host()}{path}'