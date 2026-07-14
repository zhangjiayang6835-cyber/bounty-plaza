# fix_log_injection.py
import json
import re
from datetime import datetime

class LogInjectionProtection:
    """Protect against log injection / log forging attacks."""

    @staticmethod
    def sanitize_log_input(input_str):
        """Remove or escape CRLF characters from log input."""
        if not input_str:
            return input_str
        # Remove CR and LF characters
        result = input_str.replace('\r', '')
        result = result.replace('\n', '')
        # Also remove other control characters
        result = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', result)
        return result

    @staticmethod
    def make_structured_log(event_type, **kwargs):
        """Create a structured JSON log entry with sanitized values."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
        }
        for key, value in kwargs.items():
            if isinstance(value, str):
                log_entry[key] = LogInjectionProtection.sanitize_log_input(value)
            else:
                log_entry[key] = value
        return json.dumps(log_entry, ensure_ascii=False)

    @staticmethod
    def validate_log_schema(log_entry):
        """Validate that a log entry matches the expected schema."""
        required_fields = ['timestamp', 'event_type']
        for field in required_fields:
            if field not in log_entry:
                return False
        return True