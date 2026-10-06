"""JWT Key ID (kid) Whitelist Resolver & Path Traversal Defense.
Resolves Issue #286: JWT Kid Injection -> Path Traversal -> Secret Key Leak ($150).
"""

import re
from typing import Dict, List, Optional, Set


class JWTKeyResolutionError(Exception):
    """Raised when JWT 'kid' header parameter is invalid, malicious, or unmapped."""
    pass


class InsecureKeyPathError(JWTKeyResolutionError):
    """Raised when path traversal characters (../, /, \\, NUL) are detected in kid."""
    pass


# Strict alphanumeric + hyphen/underscore identifier pattern for Key IDs
SAFE_KID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


class JWTKeyResolver:
    """Manages Key ID (kid) mapping strictly using in-memory whitelist enumeration.
    Never constructs or accesses filesystem paths from user-provided 'kid' values.
    """

    def __init__(self, key_store: Optional[Dict[str, bytes]] = None):
        """Initialize resolver with predefined in-memory key mappings.

        Args:
            key_store: Dict mapping verified kid -> secret/public key bytes.
        """
        self._key_store: Dict[str, bytes] = dict(key_store or {})

    def register_key(self, kid: str, key_bytes: bytes) -> None:
        """Register a valid Key ID into the static whitelist."""
        clean_kid = self.validate_kid_format(kid)
        if not key_bytes:
            raise ValueError("Key material must not be empty")
        self._key_store[clean_kid] = key_bytes

    @property
    def registered_kids(self) -> Set[str]:
        """Return the set of recognized Key IDs."""
        return set(self._key_store.keys())

    @staticmethod
    def validate_kid_format(kid: Optional[str]) -> str:
        """Validate and normalize 'kid' input.

        Strictly forbids directory traversal sequences, slashes, null bytes,
        or absolute paths.

        Args:
            kid: Untrusted 'kid' string from JWT header.

        Returns:
            Normalized kid string.

        Raises:
            InsecureKeyPathError: If traversal or illegal characters are found.
            JWTKeyResolutionError: If kid is empty or malformed.
        """
        if not kid or not isinstance(kid, str):
            raise JWTKeyResolutionError("JWT 'kid' header parameter must be a non-empty string.")

        clean_kid = kid.strip()
        if not clean_kid:
            raise JWTKeyResolutionError("JWT 'kid' cannot be empty or pure whitespace.")

        # Prohibit path traversal patterns explicitly
        if (
            ".." in clean_kid
            or "/" in clean_kid
            or "\\" in clean_kid
            or "\x00" in clean_kid
            or clean_kid.startswith(".")
        ):
            raise InsecureKeyPathError(
                f"Path traversal sequence detected in JWT 'kid': '{clean_kid}'. Filesystem key lookup is prohibited."
            )

        # Enforce strict identifier character set (alphanumeric, underscore, hyphen)
        if not SAFE_KID_PATTERN.match(clean_kid):
            raise InsecureKeyPathError(
                f"Invalid 'kid' format: '{clean_kid}'. Must match pattern '^[a-zA-Z0-9_-]{{1,64}}$'."
            )

        return clean_kid

    def resolve_key(self, kid: Optional[str]) -> bytes:
        """Resolve verification key strictly through in-memory dictionary lookup.

        Args:
            kid: Untrusted 'kid' string from JWT header.

        Returns:
            bytes: The secret or public key bytes associated with the authorized kid.

        Raises:
            InsecureKeyPathError: If path traversal syntax is supplied.
            JWTKeyResolutionError: If kid is not found in the whitelist.
        """
        clean_kid = self.validate_kid_format(kid)

        # Invariant: Must exist in predefined in-memory store
        key = self._key_store.get(clean_kid)
        if key is None:
            raise JWTKeyResolutionError(
                f"Unknown Key ID '{clean_kid}'. Kid must match one of the predefined whitelist IDs: {sorted(list(self.registered_kids))}"
            )

        return key
