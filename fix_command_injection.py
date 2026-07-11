# fix_command_injection.py
import re
import smtplib
from email.mime.text import MIMEText
from email.utils import parseaddr

class CommandInjectionProtection:
    """Protect against blind command injection via email headers."""

    SHELL_METACHARS = r'[;&|`$(){}!<>#~*?\[\]\\]'

    @staticmethod
    def sanitize_header(header_value):
        """Remove shell metacharacters from email header values."""
        if not header_value:
            return header_value
        return re.sub(CommandInjectionProtection.SHELL_METACHARS, '', header_value)

    @staticmethod
    def validate_email(email):
        """Validate an email address format."""
        parsed = parseaddr(email)
        if not parsed[1] or '@' not in parsed[1]:
            return None
        return parsed[1]

    @staticmethod
    def send_email_secure(to_addr, subject, body, from_addr='noreply@example.com'):
        """
        Send email securely without using shell commands.
        Uses smtplib directly instead of system mail command.
        """
        # Validate and sanitize all inputs
        to_addr = CommandInjectionProtection.validate_email(to_addr)
        if not to_addr:
            raise ValueError("Invalid recipient email address")

        sanitized_subject = CommandInjectionProtection.sanitize_header(subject)
        sanitized_body = CommandInjectionProtection.sanitize_header(body)

        # Use smtplib instead of shell commands
        msg = MIMEText(sanitized_body)
        msg['Subject'] = sanitized_subject
        msg['From'] = from_addr
        msg['To'] = to_addr

        return msg.as_string()