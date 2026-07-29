import socket
import ipaddress

def validate_destination_ip_not_internal(hostname: str) -> str:
    """Validates destination hostname IP to prevent Blind SSRF and DNS Rebinding (Issue #307)."""
    ip_str = socket.gethostbyname(hostname)
    ip_obj = ipaddress.ip_address(ip_str)

    if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
        raise SecurityError(f"SSRF Protection Blocked: Resolved IP '{ip_str}' is internal/private.")

    return ip_str
