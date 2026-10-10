# fix_clickjacking_39.py
"""
Clickjacking Protection for issue #39.

Sets security headers to prevent the application from being embedded in iframes.
"""

class ClickjackingProtection39:
    """Protect against clickjacking attacks with frame-related security headers."""

    @staticmethod
    def get_security_headers():
        """Return security headers to prevent clickjacking."""
        return {
            # Prevent any framing
            'X-Frame-Options': 'DENY',
            # CSP frame-ancestors
            'Content-Security-Policy': "default-src 'self'; frame-ancestors 'none'; sandbox allow-scripts",
            # Additional protection
            'X-Content-Type-Options': 'nosniff',
            'X-XSS-Protection': '1; mode=block',
        }

    @staticmethod
    def get_frame_busting_script():
        """Return frame busting JavaScript for legacy browser support."""
        return """
// Frame busting script for legacy browsers
if (window.top !== window.self) {
    window.top.location = window.self.location;
}
"""

    @staticmethod
    def apply_flask_middleware(app):
        """Apply clickjacking protection as Flask middleware."""
        from flask import request, g

        @app.before_request
        def add_clickjacking_headers():
            headers = ClickjackingProtection39.get_security_headers()
            for key, value in headers.items():
                g.setdefault('response_headers', {})[key] = value

        @app.after_request
        def set_response_headers(response):
            headers = ClickjackingProtection39.get_security_headers()
            for key, value in headers.items():
                response.headers[key] = value
            return response

        return app

    @staticmethod
    def apply_fastapi_middleware(app):
        """Apply clickjacking protection as FastAPI middleware."""
        from starlette.middleware.base import BaseHTTPMiddleware

        class ClickjackingMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                response = await call_next(request)
                headers = ClickjackingProtection39.get_security_headers()
                for key, value in headers.items():
                    response.headers[key] = value
                return response

        app.add_middleware(ClickjackingMiddleware)
        return app

    @staticmethod
    def get_nginx_config():
        """Return Nginx configuration for clickjacking protection."""
        return """
# Clickjacking protection headers
add_header X-Frame-Options "DENY" always;
add_header Content-Security-Policy "frame-ancestors 'none'" always;
add_header X-Content-Type-Options "nosniff" always;
"""

    @staticmethod
    def get_apache_config():
        """Return Apache configuration for clickjacking protection."""
        return """
# Clickjacking protection headers
Header always set X-Frame-Options "DENY"
Header always set Content-Security-Policy "frame-ancestors 'none'"
Header always set X-Content-Type-Options "nosniff"
"""