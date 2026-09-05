"""Structured Log Injection & SIEM Poisoning Defense Engine.
Resolves Issue #301: Log Injection → Log Forging → SIEM Poisoning ($120 USD / 150 coins).
Upstream Reference: zhangjiayang6835-cyber/ai-research#951 / CWE-117 (Improper Output Handling for Logs).

Acceptance Criteria:
- Sanitizes / escapes CRLF control characters (\r, \n) from all untrusted inputs
- Enforces strict structured NDJSON output ensuring 1 log entry = exactly 1 physical line
- Implements strict schema validation (timestamp, level, service, event_type, message, metadata)
- Prevents SIEM poisoning, log splitting, and forged authorization log events
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import re
from typing import Any, ClassVar, Dict, Optional, Set


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogSecurityValidationError(ValueError):
    """Raised when log data violates structural integrity or schema boundaries."""
    pass


class CRLFSanitizer:
    """Detects and escapes or strips CRLF and terminal control sequences from untrusted inputs."""

    CRLF_PATTERN = re.compile(r"[\r\n]+")
    CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
    ANSI_ESCAPE_PATTERN = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    @classmethod
    def sanitize(cls, val: Any) -> Any:
        """Recursively sanitizes values, escaping carriage returns and newlines."""
        if isinstance(val, str):
            # Strip ANSI terminal escape sequences
            cleaned = cls.ANSI_ESCAPE_PATTERN.sub("", val)
            # Strip non-printable control characters
            cleaned = cls.CONTROL_CHAR_PATTERN.sub("", cleaned)
            # Escape CRLF to prevent log line splitting / log forging
            cleaned = cleaned.replace("\r", "\\r").replace("\n", "\\n")
            return cleaned
        elif isinstance(val, dict):
            return {cls.sanitize(k): cls.sanitize(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [cls.sanitize(item) for item in val]
        return val


@dataclass
class LogSchema:
    """Enforces strict schema constraints on structured log records."""

    service: str
    level: LogLevel
    event_type: str
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Class-level policy, not mutable per-record state.
    ALLOWED_LEVELS: ClassVar[Set[str]] = {lvl.value for lvl in LogLevel}

    def validate(self) -> None:
        """Validates all required fields and invariants."""
        if not self.service or not self.service.strip():
            raise LogSecurityValidationError("Log field 'service' must be non-empty")
        if not isinstance(self.level, LogLevel) or self.level.value not in self.ALLOWED_LEVELS:
            raise LogSecurityValidationError(f"Invalid log level '{self.level}'")
        if not self.event_type or not self.event_type.strip():
            raise LogSecurityValidationError("Log field 'event_type' must be non-empty")
        if not self.message or not self.message.strip():
            raise LogSecurityValidationError("Log field 'message' must be non-empty")

        # Invariant: ISO8601 timestamp validation
        try:
            datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        except Exception as exc:
            raise LogSecurityValidationError(f"Invalid ISO timestamp '{self.timestamp}': {exc}")


class StructuredSecureLogger:
    """Formats, sanitizes, validates, and serializes logs into atomic single-line JSON records."""

    def __init__(self, service_name: str, default_metadata: Optional[Dict[str, Any]] = None):
        self.service_name = CRLFSanitizer.sanitize(service_name)
        self.default_metadata = CRLFSanitizer.sanitize(default_metadata or {})

    def create_log_entry(
        self,
        level: LogLevel,
        event_type: str,
        message: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Constructs and validates a sanitized structured log dictionary."""
        # Sanitize all untrusted inputs
        safe_event_type = CRLFSanitizer.sanitize(event_type)
        safe_message = CRLFSanitizer.sanitize(message)
        safe_user_id = CRLFSanitizer.sanitize(user_id) if user_id is not None else None
        safe_ip_address = CRLFSanitizer.sanitize(ip_address) if ip_address is not None else None
        safe_user_agent = CRLFSanitizer.sanitize(user_agent) if user_agent is not None else None

        merged_metadata = dict(self.default_metadata)
        if metadata is not None:
            if not isinstance(metadata, dict):
                raise LogSecurityValidationError("Log field 'metadata' must be an object")
            merged_metadata.update(CRLFSanitizer.sanitize(metadata))

        schema = LogSchema(
            service=self.service_name,
            level=level,
            event_type=safe_event_type,
            message=safe_message,
            user_id=safe_user_id,
            ip_address=safe_ip_address,
            user_agent=safe_user_agent,
            metadata=merged_metadata,
        )
        schema.validate()

        return {
            "timestamp": schema.timestamp,
            "level": schema.level.value,
            "service": schema.service,
            "event_type": schema.event_type,
            "message": schema.message,
            "user_id": schema.user_id,
            "ip_address": schema.ip_address,
            "user_agent": schema.user_agent,
            "metadata": schema.metadata,
        }

    def format_line(
        self,
        level: LogLevel,
        event_type: str,
        message: str,
        **kwargs: Any
    ) -> str:
        """Serializes log record to a single NDJSON line. Guaranteed no physical newlines."""
        entry = self.create_log_entry(level=level, event_type=event_type, message=message, **kwargs)
        serialized = json.dumps(entry, ensure_ascii=True, separators=(",", ":"))
        # Invariant check: Output serialized line must never contain raw unescaped newlines
        assert "\n" not in serialized, "Invariant violated: raw newline in structured JSON log line"
        assert "\r" not in serialized, "Invariant violated: raw CR in structured JSON log line"
        return serialized
