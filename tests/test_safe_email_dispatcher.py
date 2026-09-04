import pytest
from scripts.safe_email_dispatcher import (
    SafeEmailDispatcher,
    sanitize_header_field,
    validate_email_address,
    EmailSecurityError,
)


def test_sanitize_header_field_strips_crlf():
    malicious_subject = "Welcome!\r\nBcc: victim@example.com\r\nSubject: Injected"
    clean = sanitize_header_field(malicious_subject, field_name="Subject")
    assert "\r" not in clean
    assert "\n" not in clean
    assert clean == "Welcome! Bcc: victim@example.com Subject: Injected"


def test_sanitize_header_field_rejects_empty():
    with pytest.raises(EmailSecurityError):
        sanitize_header_field("", field_name="Subject")
    with pytest.raises(EmailSecurityError):
        sanitize_header_field("   \r\n   ", field_name="Subject")


def test_validate_email_address_blocks_shell_characters():
    # Shell injection payloads
    dangerous_recipients = [
        "user@example.com; rm -rf /",
        "user@example.com | id",
        "user@example.com `touch /tmp/pwn`",
        "user@example.com $(whoami)",
        "user@example.com & cat /etc/passwd",
        "user@example.com\r\nInjected: true",
    ]
    for bad_email in dangerous_recipients:
        with pytest.raises(EmailSecurityError) as excinfo:
            validate_email_address(bad_email)
        assert "Dangerous shell characters detected" in str(excinfo.value) or "Invalid email" in str(excinfo.value)


def test_validate_email_address_valid():
    valid = validate_email_address("alice.security@bountyplaza.dev")
    assert valid == "alice.security@bountyplaza.dev"


def test_safe_email_dispatcher_build_and_send():
    dispatcher = SafeEmailDispatcher(sender_email="notifications@bountyplaza.dev")
    msg = dispatcher.build_message(
        recipient="bounty-hunter@example.com",
        subject="Your Bounty Submission is Approved\r\n",
        body_text="Congratulations! Your patch was successfully merged.",
        body_html="<p>Congratulations! Your patch was successfully merged.</p>",
    )

    assert msg["From"] == "notifications@bountyplaza.dev"
    assert msg["To"] == "bounty-hunter@example.com"
    assert "\r" not in msg["Subject"]
    assert "\n" not in msg["Subject"]
    assert msg["Subject"] == "Your Bounty Submission is Approved"

    result = dispatcher.send_via_mock_smtp(msg)
    assert result["status"] == "SENT"
    assert result["subject"] == "Your Bounty Submission is Approved"
