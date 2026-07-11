# fix_redos.py
"""
ReDoS (Regular Expression Denial of Service) Protection for issue #77.

ReDoS vulnerabilities occur when a regex has overlapping alternatives that
cause exponential backtracking on malicious input.

Common vulnerable patterns:
  - (a+)+$
  - (.*).*(.*)
  - (a|a)+
  - ([a-zA-Z]+[0-9]+)+
"""

import re
import signal
from functools import wraps

class ReDoSProtection:
    """Protect against Regular Expression Denial of Service attacks."""

    # Maximum input length before regex processing
    MAX_INPUT_LENGTH = 1000

    # Maximum regex matching time in seconds
    MAX_REGEX_TIME = 0.5

    # Safe regex replacements for common vulnerable patterns
    SAFE_REPLACEMENTS = {
        # Vulnerable: (a+)+$  →  Safe: a+$
        r'(a+)\+': r'a+',
        # Vulnerable: (.*).*(.*)  →  Safe: use string methods
        r'\(.*\).*\(\)': None,  # Replace with non-regex solution
        # Vulnerable: (a|a)+  →  Safe: a+
        r'\(a\|a\)\+': r'a+',
        # Vulnerable: ([a-zA-Z]+[0-9]+)+  →  Safe: [a-zA-Z]+[0-9]+
        r'\(\[a-zA-Z\]\+\[0-9\]\+\)\+': r'[a-zA-Z]+[0-9]+',
    }

    @staticmethod
    def validate_input_length(input_str, max_length=None):
        """Validate input length to prevent ReDoS."""
        if max_length is None:
            max_length = ReDoSProtection.MAX_INPUT_LENGTH

        if not isinstance(input_str, str):
            return False
        if len(input_str) > max_length:
            return False
        return True

    @staticmethod
    def is_vulnerable_pattern(pattern):
        """Check if a regex pattern might be vulnerable to ReDoS."""
        # Check for common vulnerable patterns
        vulnerable_patterns = [
            r'\(\.\*\)\.\*',        # (.*).*
            r'\(.+\)\+',           # (.+)+
            r'\(\[.\]\+\)\+',      # ([\w]+)+
            r'\(\|\)',             # (a|a) style
            r'\(.*\)',             # Capturing group with .*
        ]
        for vp in vulnerable_patterns:
            if re.search(vp, pattern):
                return True
        return False

    @staticmethod
    def safe_regex_match(pattern, input_str, max_time=None):
        """
        Safely match regex pattern with timeout protection.
        Raises TimeoutError if matching takes too long.
        """
        if max_time is None:
            max_time = ReDoSProtection.MAX_REGEX_TIME

        # Validate input length
        if not ReDoSProtection.validate_input_length(input_str):
            raise ValueError("Input too long for regex matching")

        # Compile pattern
        try:
            compiled = re.compile(pattern)
        except re.error:
            return None

        # Use signal-based timeout (Unix only)
        def handler(signum, frame):
            raise TimeoutError("Regex matching timed out - possible ReDoS")

        if hasattr(signal, 'alarm'):
            old_handler = signal.signal(signal.SIGALRM, handler)
            signal.alarm(int(max_time * 1000) // 1000 or 1)
            try:
                match = compiled.match(input_str)
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
                return match
            except TimeoutError:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
                raise

        # Fallback: simple match without timeout
        return compiled.match(input_str)

    @staticmethod
    def safe_regex_search(pattern, input_str, max_time=None):
        """Safely search regex pattern with timeout protection."""
        if max_time is None:
            max_time = ReDoSProtection.MAX_REGEX_TIME

        if not ReDoSProtection.validate_input_length(input_str):
            raise ValueError("Input too long for regex matching")

        try:
            compiled = re.compile(pattern)
        except re.error:
            return None

        if hasattr(signal, 'alarm'):
            old_handler = signal.signal(signal.SIGALRM, lambda s, f: raise TimeoutError())
            signal.alarm(1)
            try:
                match = compiled.search(input_str)
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
                return match
            except TimeoutError:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
                raise

        return compiled.search(input_str)

    @staticmethod
    def safe_email_validation(email):
        """
        Safely validate email without vulnerable regex.
        Uses simple string operations instead of complex regex.
        """
        if not email or not isinstance(email, str):
            return False

        # Length check
        if len(email) > 254:
            return False

        # Basic format check
        if '@' not in email:
            return False

        local, domain = email.rsplit('@', 1)
        if not local or not domain:
            return False

        # Domain must have at least one dot
        if '.' not in domain:
            return False

        # Check for valid characters
        safe_chars = set('abcdefghijklmnopqrstuvwxyz0123456789._%-@')
        if not all(c.lower() in safe_chars for c in email):
            return False

        # Check for consecutive dots
        if '..' in email:
            return False

        return True

    @staticmethod
    def safe_url_validation(url):
        """Safely validate URL without vulnerable regex."""
        from urllib.parse import urlparse

        if not url or not isinstance(url, str):
            return False

        if len(url) > 2048:
            return False

        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False

        return bool(parsed.netloc)

    @staticmethod
    def get_security_config():
        """Return ReDoS security configuration."""
        return {
            'max_input_length': ReDoSProtection.MAX_INPUT_LENGTH,
            'max_regex_time': ReDoSProtection.MAX_REGEX_TIME,
            'use_safe_alternatives': True,
            'enable_timeout': True,
        }