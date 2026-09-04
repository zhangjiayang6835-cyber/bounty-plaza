import json
import pytest
from scripts.safe_logger import (
    StructuredSafeLogger,
    sanitize_string,
    sanitize_log_payload,
    LogValidationError,
)


def test_sanitize_string_crlf_removal():
    malicious_input = "admin\r\n2026-09-04 12:00:00 [CRITICAL] Fake forged log entry"
    cleaned = sanitize_string(malicious_input)
    assert "\r" not in cleaned
    assert "\n" not in cleaned
    assert "Fake forged log entry" in cleaned


def test_sanitize_log_payload_nested():
    nested_data = {
        "user\r\nname": "alice\nadmin",
        "headers": ["User-Agent: Mozilla\r\nInjected-Header: evil", "Accept: */*"],
        "metadata": {
            "query": "SELECT * FROM users\r\n-- comment"
        }
    }
    clean = sanitize_log_payload(nested_data)
    assert "user name" in clean
    assert "alice admin" in clean["user name"]
    assert "\r" not in clean["headers"][0]
    assert "\n" not in clean["headers"][0]
    assert "\r" not in clean["metadata"]["query"]
    assert "\n" not in clean["metadata"]["query"]


def test_structured_safe_logger_output():
    logger = StructuredSafeLogger(service_name="auth-service\r\n")
    log_line = logger.format_entry(
        level="info",
        message="User login succeeded\r\n forged message",
        extra={"username": "bob\nroot", "attempts": 1},
        timestamp="2026-09-04T12:00:00Z"
    )

    # Must be single line (no newlines)
    assert "\n" not in log_line
    assert "\r" not in log_line

    # Must be valid JSON
    parsed = json.loads(log_line)
    assert parsed["service"] == "auth-service"
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "User login succeeded  forged message"
    assert parsed["context"]["username"] == "bob root"
    assert parsed["context"]["attempts"] == 1
    assert parsed["timestamp"] == "2026-09-04T12:00:00Z"


def test_structured_safe_logger_invalid_level():
    logger = StructuredSafeLogger()
    with pytest.raises(LogValidationError) as excinfo:
        logger.format_entry(level="UNKNOWN_LEVEL", message="Test message")
    assert "Invalid log level" in str(excinfo.value)


def test_structured_safe_logger_invalid_extra():
    logger = StructuredSafeLogger()
    with pytest.raises(LogValidationError) as excinfo:
        logger.format_entry(level="INFO", message="Test message", extra=["not", "a", "dict"])  # type: ignore
    assert "'extra' context must be a dictionary" in str(excinfo.value)
