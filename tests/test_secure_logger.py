import json
import pytest
from scripts.secure_logger import (
    StructuredSecureLogger,
    CRLFSanitizer,
    LogLevel,
    LogSecurityValidationError,
)


def test_crlf_sanitizer_escapes_newlines_and_carriage_returns():
    malicious_input = "alice_admin\r\n[2026-09-04 12:00:00] [CRITICAL] [auth] System admin token generated"
    sanitized = CRLFSanitizer.sanitize(malicious_input)

    assert "\r" not in sanitized
    assert "\n" not in sanitized
    assert "\\r\\n" in sanitized
    assert "alice_admin" in sanitized


def test_crlf_sanitizer_removes_ansi_escapes_and_control_chars():
    ansi_payload = "\x1B[31mRedAlert\x1B[0m\x00\x08malformed"
    sanitized = CRLFSanitizer.sanitize(ansi_payload)

    assert "\x1B" not in sanitized
    assert "\x00" not in sanitized
    assert "\x08" not in sanitized
    assert "RedAlertmalformed" == sanitized


def test_structured_logger_atomic_single_line_output():
    logger = StructuredSecureLogger(service_name="payment_gateway\r\nINJECTED")
    user_agent_attack = "Mozilla/5.0\nHTTP/1.1 200 OK\r\nSet-Cookie: admin=true"

    log_line = logger.format_line(
        level=LogLevel.WARN,
        event_type="UNAUTHORIZED_ACCESS_ATTEMPT",
        message="User failed login challenge\r\nSTATUS: GRANTED_FORGED",
        user_id="user_12345\nADMIN",
        ip_address="192.168.1.100",
        user_agent=user_agent_attack,
        metadata={"attempt_count": 3, "nested": {"param": "val\r\ninjected"}},
    )

    # Invariant: Must be strictly one physical line
    assert "\n" not in log_line
    assert "\r" not in log_line

    # Must be valid parseable JSON
    parsed = json.loads(log_line)
    assert parsed["level"] == "WARN"
    assert "payment_gateway\\r\\nINJECTED" == parsed["service"]
    assert "User failed login challenge\\r\\nSTATUS: GRANTED_FORGED" == parsed["message"]
    assert "user_12345\\nADMIN" == parsed["user_id"]
    assert "Mozilla/5.0\\nHTTP/1.1 200 OK\\r\\nSet-Cookie: admin=true" == parsed["user_agent"]
    assert parsed["metadata"]["nested"]["param"] == "val\\r\\ninjected"


def test_structured_logger_schema_validation_enforcement():
    logger = StructuredSecureLogger(service_name="auth_service")

    # Empty event_type must fail validation
    with pytest.raises(LogSecurityValidationError, match="event_type"):
        logger.create_log_entry(
            level=LogLevel.INFO,
            event_type="",
            message="Valid message",
        )

    # Empty message must fail validation
    with pytest.raises(LogSecurityValidationError, match="message"):
        logger.create_log_entry(
            level=LogLevel.INFO,
            event_type="USER_LOGIN",
            message="   ",
        )


def test_structured_logger_rejects_untyped_levels_and_metadata():
    logger = StructuredSecureLogger(service_name="auth_service")

    with pytest.raises(LogSecurityValidationError, match="Invalid log level"):
        logger.create_log_entry(
            level="INFO",  # type: ignore[arg-type]
            event_type="USER_LOGIN",
            message="Valid message",
        )

    with pytest.raises(LogSecurityValidationError, match="metadata.*object"):
        logger.create_log_entry(
            level=LogLevel.INFO,
            event_type="USER_LOGIN",
            message="Valid message",
            metadata=["forged", "entry"],  # type: ignore[arg-type]
        )


def test_default_metadata_is_copied_and_sanitized():
    defaults = {"source": "edge\r\nFORGED", "request": {"id": "a\nb"}}
    logger = StructuredSecureLogger("gateway", defaults)
    defaults["source"] = "mutated"

    parsed = json.loads(logger.format_line(LogLevel.INFO, "REQUEST", "accepted"))

    assert parsed["metadata"] == {"source": "edge\\r\\nFORGED", "request": {"id": "a\\nb"}}
