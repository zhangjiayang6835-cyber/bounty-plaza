import re

def sanitize_ldap_input(user_input: str) -> str:
    """Sanitizes user input to prevent LDAP Injection attacks (Issue #297)."""
    if not user_input:
        return ""
    # Escape special LDAP filter characters
    escaped = re.sub(r'\\', r'\\5c', user_input)
    escaped = re.sub(r'\*', r'\\2a', escaped)
    escaped = re.sub(r'\(', r'\\28', escaped)
    escaped = re.sub(r'\)', r'\\29', escaped)
    escaped = re.sub(r'\x00', r'\\00', escaped)
    return escaped

def build_ldap_search_filter(username: str) -> str:
    safe_username = sanitize_ldap_input(username)
    return f"(&(objectClass=user)(uid={safe_username}))"
