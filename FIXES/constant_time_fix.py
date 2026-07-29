import hmac

def constant_time_password_compare(val1: str, val2: str) -> bool:
    """Uses HMAC constant-time comparison to prevent password timing attacks (Issue #289)."""
    if not isinstance(val1, str) or not isinstance(val2, str):
        return False
    return hmac.compare_digest(val1.encode('utf-8'), val2.encode('utf-8'))
