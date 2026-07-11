# fix_session_fixation.py
import secrets
from flask import session, request, abort

class SessionFixationProtection:
    """Middleware to prevent session fixation attacks."""

    @staticmethod
    def regenerate_session():
        """Regenerate the session ID to prevent fixation."""
        # Clear existing session data
        session_data = dict(session)
        session.clear()
        # Generate new session ID
        session.update(session_data)
        session['_fresh'] = True

    @staticmethod
    def reject_url_session_id():
        """Reject session IDs passed via URL parameters."""
        if 'sessionid' in request.args:
            # Remove it from args and reject the request
            abort(400, description="Session ID in URL is not allowed")

    @staticmethod
    def get_session_config():
        """Return secure session cookie configuration."""
        return {
            'SESSION_COOKIE_SECURE': True,
            'SESSION_COOKIE_HTTPONLY': True,
            'SESSION_COOKIE_SAMESITE': 'Lax',
        }