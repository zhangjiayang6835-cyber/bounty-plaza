# fix_xss_search.py
"""
Reflected XSS Protection for search parameter (issue #40).

XSS vulnerabilities occur when user input is reflected in HTML output
without proper sanitization.
"""

import html
import re

class ReflectedXSSProtection:
    """Protect against reflected XSS in search parameters and similar inputs."""

    # Characters to escape for safe HTML output
    HTML_ESCAPE_MAP = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '/': '&#x2F;',
    }

    @classmethod
    def escape_html(cls, input_str):
        """
        Escape HTML special characters in user input.
        This is the primary defense against XSS.
        """
        if not input_str:
            return ''

        # Use Python's html.escape for basic escaping
        escaped = html.escape(str(input_str), quote=True)
        return escaped

    @classmethod
    def sanitize_search_query(cls, query):
        """
        Sanitize a search query for safe HTML output.
        """
        if not query:
            return ''

        # Escape HTML entities
        sanitized = cls.escape_html(query)

        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')

        return sanitized

    @classmethod
    def get_csp_headers(cls):
        """Return Content Security Policy headers."""
        return {
            'Content-Security-Policy': (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'"
            ),
            'X-Content-Type-Options': 'nosniff',
            'X-XSS-Protection': '1; mode=block',
        }

    @classmethod
    def render_safe_search_result(cls, query, results):
        """
        Safely render search results with escaped query.
        """
        safe_query = cls.sanitize_search_query(query)

        # Build HTML template safely
        html_parts = [
            '<div class="search-results">',
            '<h2>Search results for: %s</h2>' % safe_query,
            '<ul>',
        ]

        for result in results:
            safe_title = cls.escape_html(result.get('title', ''))
            safe_url = cls.escape_html(result.get('url', ''))
            html_parts.append(
                '<li><a href="%s">%s</a></li>' % (safe_url, safe_title)
            )

        html_parts.append('</ul></div>')
        return '\n'.join(html_parts)

    @staticmethod
    def is_xss_payload(input_str):
        """Detect potential XSS payloads in user input."""
        if not input_str:
            return False

        xss_patterns = [
            r'<\s*script',
            r'javascript:',
            r'vbscript:',
            r'on\w+\s*=',
            r'<\s*iframe',
            r'<\s*object',
            r'<\s*embed',
            r'<\s*svg',
            r'expression\s*\(',
        ]

        lower_input = input_str.lower()
        for pattern in xss_patterns:
            if re.search(pattern, lower_input):
                return True

        return False

    @classmethod
    def sanitize_url(cls, url):
        """
        Sanitize URL for safe HTML output.
        Prevents javascript: and data: URL injection.
        """
        if not url:
            return '#'

        # Block dangerous URL schemes
        dangerous_schemes = ['javascript:', 'vbscript:', 'data:', 'file:']
        url_lower = url.lower().strip()

        for scheme in dangerous_schemes:
            if url_lower.startswith(scheme):
                return '#'

        # Escape HTML entities
        return cls.escape_html(url)

    @staticmethod
    def get_nginx_xss_config():
        """Return Nginx configuration for XSS protection headers."""
        return """
# XSS protection headers
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; frame-ancestors 'none'" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
"""