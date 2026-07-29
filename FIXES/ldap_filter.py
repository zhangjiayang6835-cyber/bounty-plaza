import re

def sanitize_ldap_search_filter(input_str: str) -> str:
    """Escapes special LDAP query characters preventing LDAP Injection (Issue #267)."""
    if not isinstance(input_str, str):
        return ""
    
    # Escape LDAP special filter characters: *, (, ), \, \x00
    escaped = input_str.replace('\\', '\\5c')
    escaped = escaped.replace('*', '\\2a')
    escaped = escaped.replace('(', '\\28')
    escaped = escaped.replace(')', '\\29')
    escaped = escaped.replace('\x00', '\\00')
    return escaped
