# fix_clickjacking.py
from functools import wraps
from flask import request, session, jsonify

class ClickjackingProtection:
    """Middleware to protect against clickjacking attacks."""

    @staticmethod
    def get_headers():
        """Return security headers for clickjacking prevention."""
        return {
            'X-Frame-Options': 'DENY',
            'Content-Security-Policy': "frame-ancestors 'none'",
        }

    @staticmethod
    def require_confirmation(route_func):
        """Decorator: require explicit confirmation for critical operations."""
        @wraps(route_func)
        def wrapper(*args, **kwargs):
            confirmed = request.form.get('confirm_withdrawal')
            if confirmed != 'yes':
                return jsonify({
                    'error': 'Confirmation required',
                    'message': 'Please confirm this withdrawal by adding confirm_withdrawal=yes'
                }), 400
            return route_func(*args, **kwargs)
        return wrapper
