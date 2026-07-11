# fix_totp_leak.py
import re

class TOTPLeakProtection:
    """Protect against TOTP secret leaking via QR codes in logs."""

    # Patterns that look like TOTP secrets or QR code data
    SENSITIVE_PATTERNS = [
        r'otpauth://totp/[^\s\'"]+',
        r'otpauth://hotp/[^\s\'"]+',
        r'secret[=:]["\']?[A-Za-z0-9]{16,64}',
        r'totp_secret["\']?\s*[:=]\s*["\']?[A-Za-z0-9]{16,64}',
        r'2fa_secret["\']?\s*[:=]\s*["\']?[A-Za-z0-9]{16,64}',
        r'qr_code[=\s:]+[A-Za-z0-9+/]{20,}={0,2}',
        r'data:image/[^;\s]+;base64,[A-Za-z0-9+/]{50,}={0,2}',
    ]

    @classmethod
    def mask_sensitive_data(cls, text):
        """Mask TOTP secrets and QR code data in log output."""
        if not text:
            return text

        masked = text
        for pattern in cls.SENSITIVE_PATTERNS:
            masked = re.sub(pattern, '[REDACTED_TOTP_SECRET]', masked, flags=re.IGNORECASE)
        return masked

    @classmethod
    def should_not_log(cls, data):
        """Check if data contains sensitive TOTP information."""
        for pattern in cls.SENSITIVE_PATTERNS:
            if re.search(pattern, str(data), re.IGNORECASE):
                return True
        return False

    @classmethod
    def safe_log(cls, message):
        """Log a message after masking sensitive data."""
        if cls.should_not_log(message):
            return '[REDACTED: contains TOTP secret]'
        return cls.mask_sensitive_data(message)