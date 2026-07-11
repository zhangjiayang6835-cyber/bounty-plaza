# fix_ldap_injection.py
import re

class LDAPInjectionProtection:
    """Protect against LDAP injection attacks."""

    RFC4514_SPECIAL = r'[\\*()\0]'

    @staticmethod
    def escape_ldap_filter(input_str):
        """
        Escape LDAP filter special characters per RFC 4514.
        Escapes: \\ * ( ) \0
        """
        if not input_str:
            return input_str
        result = input_str
        result = result.replace('\\', '\\5c')
        result = result.replace('*', '\\2a')
        result = result.replace('(', '\\28')
        result = result.replace(')', '\\29')
        result = result.replace('\0', '\\00')
        return result

    @staticmethod
    def validate_no_wildcard(input_str):
        """Check if input contains wildcard characters."""
        return '*' not in input_str and '?' not in input_str

    @staticmethod
    def build_secure_filter(template, **kwargs):
        """
        Build LDAP filter with escaped parameters.
        Template example: '(&(uid={uid})(userPassword={pwd}))'
        """
        escaped = {}
        for key, value in kwargs.items():
            escaped[key] = LDAPInjectionProtection.escape_ldap_filter(str(value))
        return template.format(**escaped)

    @staticmethod
    def reject_anonymous_bind(username, password):
        """Reject empty username or password (anonymous bind)."""
        if not username or not username.strip():
            return True
        if not password or not password.strip():
            return True
        return False