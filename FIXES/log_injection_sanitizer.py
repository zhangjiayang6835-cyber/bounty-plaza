import re

def sanitize_log_message(message: str) -> str:
    """Sanitizes log messages stripping CRLF characters to prevent Log Injection / Forgery (Issue #301)."""
    if not message:
        return ""
    # Strip carriage returns and line feeds
    sanitized = re.sub(r'[\r\n]', '_', str(message))
    return sanitized
