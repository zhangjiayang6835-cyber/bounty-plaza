"""Safe Email Dispatcher & SMTP/Shell Injection Defense.
Resolves Issue #81: Blind Command Injection via Email Header ($150).
Enforces zero-shell invocation, standard library EmailMessage API, and CRLF header sanitization.
"""

import re
from email.headerregistry import Address
from email.message import EmailMessage
from typing import Any, Dict, List, Optional, Union


class EmailSecurityError(ValueError):
    """Raised when email headers, recipients, or subjects violate security policies."""
    pass


CRLF_REGEX = re.compile(r"[\r\n]+")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def sanitize_header_field(value: str, field_name: str = "Header") -> str:
    """Strip Carriage Return and Line Feed characters to prevent SMTP header injection.

    Args:
        value: Untrusted user input for subject or header.
        field_name: Header name for diagnostic reporting.

    Returns:
        Clean single-line string.

    Raises:
        EmailSecurityError: If value is empty or contains pure whitespace.
    """
    if not isinstance(value, str):
        value = str(value)

    if CRLF_REGEX.search(value):
        # Strip CRLF to prevent header splitting / SMTP injection
        value = CRLF_REGEX.sub(" ", value)

    clean_value = value.strip()
    if not clean_value:
        raise EmailSecurityError(f"{field_name} cannot be empty or whitespace.")

    return clean_value


def validate_email_address(email: str, field_name: str = "Recipient") -> str:
    """Validate email address format strictly without passing through shell arguments.

    Args:
        email: Email address string.
        field_name: Field name description.

    Returns:
        Sanitized email string.

    Raises:
        EmailSecurityError: If address format is invalid or contains dangerous characters.
    """
    if not email or not isinstance(email, str):
        raise EmailSecurityError(f"{field_name} email address must be a non-empty string.")

    clean_email = email.strip()
    # Reject shell meta-characters and newlines outright
    if any(ch in clean_email for ch in (";", "&", "|", "`", "$", "(", ")", "<", ">", "\n", "\r", " ", "\t")):
        raise EmailSecurityError(
            f"Dangerous shell characters detected in {field_name} address: {clean_email}"
        )

    if not EMAIL_REGEX.match(clean_email):
        raise EmailSecurityError(f"Invalid email address format for {field_name}: {clean_email}")

    return clean_email


class SafeEmailDispatcher:
    """Constructs and dispatches emails using standard library EmailMessage API without shell execution."""

    def __init__(self, sender_email: str = "noreply@bountyplaza.dev"):
        self.sender_email = validate_email_address(sender_email, field_name="Sender")

    def build_message(
        self,
        recipient: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> EmailMessage:
        """Construct standard library EmailMessage using type-safe APIs instead of CLI sendmail arguments.

        Args:
            recipient: Validated target email address.
            subject: Email subject line (sanitized against CRLF).
            body_text: Plaintext content.
            body_html: Optional HTML version.
            extra_headers: Optional custom headers.

        Returns:
            EmailMessage object.
        """
        valid_recipient = validate_email_address(recipient, field_name="Recipient")
        clean_subject = sanitize_header_field(subject, field_name="Subject")

        msg = EmailMessage()
        msg["From"] = self.sender_email
        msg["To"] = valid_recipient
        msg["Subject"] = clean_subject

        if extra_headers:
            for k, v in extra_headers.items():
                clean_k = sanitize_header_field(k, field_name="Header key")
                clean_v = sanitize_header_field(v, field_name=f"Header {k}")
                msg[clean_k] = clean_v

        msg.set_content(body_text)

        if body_html:
            msg.add_alternative(body_html, subtype="html")

        return msg

    def send_via_mock_smtp(self, message: EmailMessage) -> Dict[str, Any]:
        """Mock dispatch verifying message generation without invoking shell or sendmail binary."""
        return {
            "status": "SENT",
            "from": message["From"],
            "to": message["To"],
            "subject": message["Subject"],
            "has_body": bool(message.get_payload()),
        }
