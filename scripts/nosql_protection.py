"""MongoDB NoSQL Injection Defense & Credential Validation Engine.
Resolves Issue #300: MongoDB NoSQL Injection -> Authentication Bypass Defense ($150).
"""

import hashlib
import hmac
import os
import secrets
from typing import Any, Dict, Optional, Tuple


class NoSQLInjectionError(ValueError):
    """Raised when query input contains illegal MongoDB operators or disallowed data types."""
    pass


class AuthenticationError(Exception):
    """Raised on invalid credentials or authentication failures."""
    pass


FORBIDDEN_OPERATORS = {
    "$ne", "$gt", "$gte", "$lt", "$lte", "$in", "$nin",
    "$where", "$regex", "$expr", "$or", "$and", "$not", "$nor",
    "$exists", "$type", "$mod", "$text", "$all", "$elemMatch", "$size"
}


def sanitize_input_value(value: Any, field_name: str = "field", max_length: int = 256) -> str:
    """Enforce strict string type validation on input values.
    Prohibits dictionaries, lists, or object injection vectors.

    Args:
        value: Untrusted user input.
        field_name: Name of the attribute for diagnostic messages.
        max_length: Maximum allowed string length.

    Returns:
        Clean trimmed string.

    Raises:
        NoSQLInjectionError: If input is not a string, is empty, or exceeds max length.
    """
    if value is None:
        raise NoSQLInjectionError(f"Missing required input for '{field_name}'")

    if not isinstance(value, str):
        raise NoSQLInjectionError(
            f"NoSQL injection vector blocked: '{field_name}' must be a string, got {type(value).__name__}"
        )

    clean_value = value.strip()
    if not clean_value:
        raise NoSQLInjectionError(f"Field '{field_name}' cannot be empty or whitespace")

    if len(clean_value) > max_length:
        raise NoSQLInjectionError(f"Field '{field_name}' exceeds maximum length of {max_length}")

    return clean_value


def sanitize_query_dict(query: Dict[str, Any]) -> Dict[str, str]:
    """Recursively validate and sanitize a query dictionary against operator injection.

    Args:
        query: Query dictionary to sanitize.

    Returns:
        Sanitized dictionary mapping string keys to string values.

    Raises:
        NoSQLInjectionError: If any key begins with '$' or matches known MongoDB operators.
    """
    if not isinstance(query, dict):
        raise NoSQLInjectionError(f"Query must be a dictionary, got {type(query).__name__}")

    clean_query: Dict[str, str] = {}
    for key, value in query.items():
        if not isinstance(key, str):
            raise NoSQLInjectionError("Query keys must be strings")

        if key.startswith("$") or key.lower() in FORBIDDEN_OPERATORS:
            raise NoSQLInjectionError(f"Forbidden MongoDB operator blocked: '{key}'")

        if isinstance(value, dict):
            # Check nested keys for operators like {"password": {"$ne": ""}}
            for sub_key in value.keys():
                if str(sub_key).startswith("$") or str(sub_key).lower() in FORBIDDEN_OPERATORS:
                    raise NoSQLInjectionError(f"Forbidden nested MongoDB operator blocked: '{sub_key}'")
            raise NoSQLInjectionError(f"Nested dictionary for field '{key}' is prohibited in value position")

        if isinstance(value, list):
            raise NoSQLInjectionError(f"List object for field '{key}' is prohibited in value position")

        clean_query[key] = sanitize_input_value(value, field_name=key)

    return clean_query


def hash_password(password: str, salt: Optional[bytes] = None, iterations: int = 100_000) -> Tuple[str, str]:
    """Derive a cryptographically secure salted PBKDF2-HMAC-SHA256 password hash.

    Args:
        password: Raw user password.
        salt: Optional salt bytes (generated randomly if None).
        iterations: PBKDF2 iteration count.

    Returns:
        Tuple of (hex_hash, hex_salt).
    """
    clean_pwd = sanitize_input_value(password, field_name="password", max_length=1024)
    if salt is None:
        salt = secrets.token_bytes(32)

    derived = hashlib.pbkdf2_hmac(
        'sha256',
        clean_pwd.encode('utf-8'),
        salt,
        iterations
    )
    return derived.hex(), salt.hex()


def verify_password(password: str, stored_hash_hex: str, stored_salt_hex: str, iterations: int = 100_000) -> bool:
    """Verify password against stored salt and hash using constant-time comparison."""
    clean_pwd = sanitize_input_value(password, field_name="password", max_length=1024)
    salt = bytes.fromhex(stored_salt_hex)
    computed_hash = hashlib.pbkdf2_hmac(
        'sha256',
        clean_pwd.encode('utf-8'),
        salt,
        iterations
    ).hex()

    return hmac.compare_digest(computed_hash, stored_hash_hex)


class SafeAuthService:
    """Mock-safe authentication repository demonstrating parameterized query construction."""

    def __init__(self):
        # user_db maps username -> {"password_hash": hex, "salt": hex, "role": str}
        self.users: Dict[str, Dict[str, str]] = {}

    def register_user(self, username: str, password: str, role: str = "user") -> Dict[str, str]:
        clean_user = sanitize_input_value(username, field_name="username")
        pwd_hash, salt = hash_password(password)
        self.users[clean_user] = {
            "username": clean_user,
            "password_hash": pwd_hash,
            "salt": salt,
            "role": role,
        }
        return {"username": clean_user, "role": role}

    def authenticate(self, credentials: Dict[str, Any]) -> Dict[str, str]:
        """Authenticate user with parameterized query and constant-time password verification.

        Args:
            credentials: Raw request dictionary (e.g. from JSON body).

        Returns:
            User profile dictionary.

        Raises:
            NoSQLInjectionError: If payload contains operator injections or non-string values.
            AuthenticationError: If credentials do not match.
        """
        # 1. Enforce query structure and reject operators
        clean = sanitize_query_dict(credentials)

        username = clean.get("username")
        password = clean.get("password")

        if not username or not password:
            raise AuthenticationError("Both username and password are required")

        user_record = self.users.get(username)
        if not user_record:
            # Prevent timing enumeration by hashing a dummy payload
            hash_password("dummy_constant_time_padding", salt=b'0'*32)
            raise AuthenticationError("Invalid username or password")

        # 2. Salted constant-time comparison
        valid = verify_password(password, user_record["password_hash"], user_record["salt"])
        if not valid:
            raise AuthenticationError("Invalid username or password")

        return {
            "username": user_record["username"],
            "role": user_record["role"]
        }
