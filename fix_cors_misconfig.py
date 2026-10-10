# fix_cors_misconfig.py
from flask import request, abort

class CORSProtection:
    """Middleware for proper CORS origin validation."""

    ALLOWED_ORIGINS = [
        'https://ai-research.example.com',
        'https://bounty-plaza.example.com',
        'http://localhost:8080',
        'http://localhost:5000',
        'http://127.0.0.1:8080',
        'http://127.0.0.1:5000',
    ]

    @classmethod
    def get_allowed_origin(cls):
        """Return the allowed origin if valid, or None."""
        origin = request.headers.get('Origin', '')
        if origin in cls.ALLOWED_ORIGINS:
            return origin
        return None

    @classmethod
    def get_cors_headers(cls):
        """Return CORS headers based on origin validation."""
        origin = cls.get_allowed_origin()
        if origin:
            return {
                'Access-Control-Allow-Origin': origin,
                'Access-Control-Allow-Credentials': 'true',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            }
        return {
            'Access-Control-Allow-Origin': 'null',
        }