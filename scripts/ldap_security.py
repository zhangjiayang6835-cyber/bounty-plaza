"""LDAP Injection Defense & Authentication Bind Validator.
Resolves Issue #297: LDAP Injection -> Anonymous Bind Bypass Defense ($120).
Compliant with RFC 4514 (DN escaping) and RFC 4515 (Search filter escaping).
"""

from typing import Optional, Tuple


class LDAPSecurityError(ValueError):
    """Base exception for LDAP validation or injection errors."""
    pass


class AnonymousBindAttemptError(LDAPSecurityError):
    """Raised when an empty username or password is supplied for binding."""
    pass


def escape_filter_value(value: str) -> str:
    """Escape special characters in user input destined for an LDAP search filter (RFC 4515).

    Characters escaped:
      - '\\' (ASCII 92) -> '\\5c'
      - '*'  (ASCII 42) -> '\\2a'
      - '('  (ASCII 40) -> '\\28'
      - ')'  (ASCII 41) -> '\\29'
      - NUL  (ASCII 0)  -> '\\00'
      - '/'  (ASCII 47) -> '\\2f'

    Args:
        value (str): The raw untrusted input string.

    Returns:
        str: RFC 4515 escaped string safe for LDAP filter concatenation.
    """
    if not isinstance(value, str):
        raise TypeError("LDAP filter value must be a string")

    # The backslash must be replaced first to avoid double-escaping
    res = []
    for ch in value:
        if ch == '\\':
            res.append(r'\5c')
        elif ch == '*':
            res.append(r'\2a')
        elif ch == '(':
            res.append(r'\28')
        elif ch == ')':
            res.append(r'\29')
        elif ch == '\x00':
            res.append(r'\00')
        elif ch == '/':
            res.append(r'\2f')
        else:
            res.append(ch)
    return ''.join(res)


def escape_dn_value(value: str) -> str:
    """Escape special characters in a Distinguished Name (DN) attribute value (RFC 4514).

    Special characters at any position: ',', '+', '"', '\\', '<', '>', ';', '\x00'.
    Leading '#' or space, and trailing space are escaped.
    """
    if not isinstance(value, str):
        raise TypeError("LDAP DN value must be a string")

    if not value:
        return ""

    escaped = []
    # Check leading char
    first = value[0]
    if first in (' ', '#'):
        escaped.append('\\' + first)
        remaining = value[1:]
    else:
        remaining = value

    # Check trailing char if length > 1
    trailing_space = False
    if len(remaining) > 0 and remaining.endswith(' '):
        trailing_space = True
        remaining = remaining[:-1]

    for ch in remaining:
        if ch in (',', '+', '"', '\\', '<', '>', ';'):
            escaped.append('\\' + ch)
        elif ch == '\x00':
            escaped.append('\\00')
        else:
            escaped.append(ch)

    if trailing_space:
        escaped.append(r'\ ')

    return ''.join(escaped)


def validate_bind_credentials(
    username: Optional[str],
    password: Optional[str]
) -> Tuple[str, str]:
    """Validate bind credentials strictly prohibiting anonymous or unauthenticated binds.

    Args:
        username: The bind user identity.
        password: The bind user secret.

    Returns:
        Tuple[str, str]: Trimmed username and password.

    Raises:
        AnonymousBindAttemptError: If username or password is empty, None, or pure whitespace.
    """
    if not username or not username.strip():
        raise AnonymousBindAttemptError("Anonymous bind rejected: Username must not be empty.")
    if not password or not password.strip():
        raise AnonymousBindAttemptError("Unauthenticated bind rejected: Password must not be empty.")

    clean_user = username.strip()
    return clean_user, password


def build_user_search_filter(username: str, base_filter: str = "objectClass=inetOrgPerson") -> str:
    """Safely construct a parameterized LDAP user lookup query.

    Args:
        username (str): Untrusted username input.
        base_filter (str): Static objectClass requirement.

    Returns:
        str: Sanitized LDAP search filter query.
    """
    if not username or not username.strip():
        raise LDAPSecurityError("Username cannot be empty")

    escaped_user = escape_filter_value(username.strip())
    return f"(&({base_filter})(uid={escaped_user}))"
