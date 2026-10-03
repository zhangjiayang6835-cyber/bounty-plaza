"""
Typed error definitions for Agent Card discovery, parsing, and validation.
"""

from typing import Any


class DiscoveryError(Exception):
    """Base exception for all agent card discovery failures."""

    def __init__(
        self, message: str, url: str | None = None, details: Any | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.url = url
        self.details = details

    def __str__(self) -> str:
        if self.url:
            return f"[{self.url}] {self.message}"
        return self.message


class InvalidUrlError(DiscoveryError):
    """Raised when an Agent Card URL is invalid or cannot be normalized."""


class NetworkError(DiscoveryError):
    """Raised when an HTTP or network-level failure occurs during card fetching."""


class ValidationError(DiscoveryError):
    """Base class for Agent Card payload validation errors."""


class MissingFieldError(ValidationError):
    """Raised when a required top-level or nested field is absent or empty."""

    def __init__(
        self, field_name: str, message: str | None = None, url: str | None = None
    ) -> None:
        msg = message or f"Missing required field: '{field_name}'"
        super().__init__(msg, url=url)
        self.field_name = field_name


class InvalidFieldTypeError(ValidationError):
    """Raised when a field has an incorrect data type."""

    def __init__(
        self,
        field_name: str,
        expected_type: str,
        actual_type: str,
        url: str | None = None,
    ) -> None:
        msg = (
            f"Field '{field_name}' expected type '{expected_type}', got '{actual_type}'"
        )
        super().__init__(msg, url=url)
        self.field_name = field_name
        self.expected_type = expected_type
        self.actual_type = actual_type


class SecurityViolationError(ValidationError):
    """Raised when an agent card exposes forbidden material such as secrets or private keys."""
