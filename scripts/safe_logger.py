"""Structured Logging & CRLF Log Injection Defense.
Resolves Issue #192: Log Injection -> Log Forging -> SIEM Poisoning Defense ($120).
"""

import datetime
import json
import re
from typing import Any, Dict, Optional, Union


class LogValidationError(ValueError):
    """Raised when log data fails schema constraints or contains invalid structures."""
    pass


ALLOWED_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
CRLF_PATTERN = re.compile(r'[\r\n]+')


def sanitize_string(value: str, replace_with: str = " ") -> str:
    """Strip or replace Carriage Return and Line Feed characters to prevent log forging.

    Args:
        value: Untrusted input string (e.g. username, User-Agent, path).
        replace_with: Replacement string for CRLF sequence (default: single space).

    Returns:
        Sanitized string safe from multi-line log injection.
    """
    if not isinstance(value, str):
        value = str(value)
    return CRLF_PATTERN.sub(replace_with, value).strip()


def sanitize_log_payload(payload: Any) -> Any:
    """Recursively sanitize any strings inside dictionary, list, or primitive fields."""
    if isinstance(payload, str):
        return sanitize_string(payload)
    elif isinstance(payload, dict):
        return {
            sanitize_string(k): sanitize_log_payload(v)
            for k, v in payload.items()
        }
    elif isinstance(payload, list):
        return [sanitize_log_payload(item) for item in payload]
    return payload


class StructuredSafeLogger:
    """Zero-dependency structured JSON logger with schema enforcement and CRLF prevention."""

    def __init__(self, service_name: str = "bounty-plaza", default_context: Optional[Dict[str, Any]] = None):
        self.service_name = sanitize_string(service_name)
        self.default_context = default_context or {}

    def format_entry(
        self,
        level: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
    ) -> str:
        """Format and validate a single structured log entry as a single-line JSON string.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            message: Primary log message (sanitized against CRLF).
            extra: Optional structured metadata dict (sanitized recursively).
            timestamp: ISO8601 UTC timestamp string (auto-generated if None).

        Returns:
            Single-line JSON string representing the SIEM-safe log record.

        Raises:
            LogValidationError: If level is invalid or extra is not a dictionary.
        """
        normalized_level = level.upper().strip()
        if normalized_level not in ALLOWED_LEVELS:
            raise LogValidationError(f"Invalid log level '{level}'. Allowed: {ALLOWED_LEVELS}")

        if extra is not None and not isinstance(extra, dict):
            raise LogValidationError(f"'extra' context must be a dictionary, got {type(extra)}")

        # Build clean timestamp
        ts = timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Sanitize message and extra payload
        clean_msg = sanitize_string(message)

        merged_context = dict(self.default_context)
        if extra:
            merged_context.update(extra)

        sanitized_context = sanitize_log_payload(merged_context)

        log_record = {
            "timestamp": ts,
            "level": normalized_level,
            "service": self.service_name,
            "message": clean_msg,
            "context": sanitized_context,
        }

        # Serialized as strict single-line JSON
        serialized = json.dumps(log_record, ensure_ascii=False, separators=(',', ':'))

        # Final assertion: Must not contain any raw newlines or carriage returns
        if '\r' in serialized or '\n' in serialized:
            raise LogValidationError("Fatal: Serialized log contains raw linebreaks")

        return serialized
