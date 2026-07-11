# fix_ldap_injection_74.py
"""
LDAP Injection Protection for issue #74.

LDAP metacharacters that must be escaped:
  \\ → \\5c
  *  → \\2a
  (  → \\28
  )  → \\29
  \0 → \\00
"""

import re

class LDAPInjectionProtection74:
    """Protect against LDAP injection in user authentication."""

    # LDAP special characters and their escaped forms
    LDAP_ESCAPE_MAP = {
        '\\': '\\5c',
        '*': '\\2a',
        '(': '\\28',
        ')': '\\29',
        '\0': '\\00',
    }

    @staticmethod
    def escape_ldap_filter(input_str):
        """Escape LDAP special characters in filter input."""
        if not input_str:
            return input_str
        result = str(input_str)
        for char, escaped in LDAPInjectionProtection74.LDAP_ESCAPE_MAP.items():
            result = result.replace(char, escaped)
        return result

    @staticmethod
    def validate_ldap_filter(filter_str):
        """
        Validate LDAP filter for injection patterns.
        Returns (safe, error) tuple.
        """
        if not filter_str:
            return False, "Empty LDAP filter"

        # Check for wildcard injection patterns
        dangerous_patterns = [
            r'\*\)',
            r'\)\*',
            r'\|\|',
            r'&&',
            r'\!\!',
            r'(uid=\*\))',
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, filter_str):
                return False, "Potentially malicious LDAP filter pattern detected"

        return True, None

    @staticmethod
    def build_secure_ldap_query(username, password):
        """
        Build a secure LDAP query for user authentication.
        Uses escaped parameters to prevent injection.
        """
        # Escape both username and password
        safe_username = LDAPInjectionProtection74.escape_ldap_filter(username)
        safe_password = LDAPInjectionProtection74.escape_ldap_filter(password)

        # Build secure filter
        base_dn = "ou=users,dc=example,dc=com"
        filter_str = "(&(uid=%s)(userPassword=%s))" % (safe_username, safe_password)

        # Validate the final filter
        valid, error = LDAPInjectionProtection74.validate_ldap_filter(filter_str)
        if not valid:
            raise ValueError(error)

        return {
            'base_dn': base_dn,
            'filter': filter_str,
            'scope': 'SUBTREE',
        }

    @staticmethod
    def reject_anonymous_bind(username, password):
        """Reject empty username or password (anonymous bind attempts)."""
        if not username or not username.strip():
            return True
        if not password or not password.strip():
            return True
        return False

    @staticmethod
    def get_ldap_security_config():
        """Return LDAP security configuration."""
        return {
            'escape_special_chars': True,
            'allow_anonymous_bind': False,
            'use_ssl': True,
            'validate_filters': True,
            'timeout': 10,
        }