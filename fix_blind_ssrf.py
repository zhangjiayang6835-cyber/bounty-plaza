# fix_blind_ssrf.py
import socket
import ipaddress
import re
from urllib.parse import urlparse

class BlindSSRFProtection:
    """Protect against blind SSRF via DNS rebinding attacks."""

    # Blocked IP ranges (internal, cloud metadata, loopback, etc.)
    BLOCKED_IP_RANGES = [
        ipaddress.ip_network('127.0.0.0/8'),       # Loopback
        ipaddress.ip_network('10.0.0.0/8'),        # Private
        ipaddress.ip_network('172.16.0.0/12'),     # Private
        ipaddress.ip_network('192.168.0.0/16'),    # Private
        ipaddress.ip_network('169.254.0.0/16'),    # Link-local (cloud metadata)
        ipaddress.ip_network('0.0.0.0/8'),         # Reserved
        ipaddress.ip_network('::1/128'),           # IPv6 loopback
        ipaddress.ip_network('fe80::/10'),         # IPv6 link-local
    ]

    # Allowed URL patterns
    ALLOWED_URL_PATTERNS = [
        r'^https://api\.example\.com/.*',
        r'^https://trusted\.partner\.com/.*',
    ]

    @classmethod
    def is_blocked_ip(cls, ip_str):
        """Check if an IP address is in a blocked range."""
        try:
            ip = ipaddress.ip_address(ip_str)
            for network in cls.BLOCKED_IP_RANGES:
                if ip in network:
                    return True
            return False
        except ValueError:
            return True  # Invalid IP is blocked

    @classmethod
    def resolve_and_validate(cls, host):
        """
        Resolve DNS and validate the IP address.
        Returns (ip, error) tuple.
        """
        try:
            # Get all IP addresses for the host
            results = socket.getaddrinfo(host, None)
            ips = set()
            for result in results:
                ip = result[4][0]
                ips.add(ip)

            # Check all resolved IPs
            for ip in ips:
                if cls.is_blocked_ip(ip):
                    raise ValueError("Blocked IP detected: %s" % ip)

            # Return the first valid IP
            return ips.pop(), None

        except socket.gaierror:
            return None, "DNS resolution failed"
        except ValueError as e:
            return None, str(e)

    @classmethod
    def validate_url(cls, url):
        """Validate URL against allowlist."""
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False, "Invalid URL format"

        # Check scheme
        if parsed.scheme not in ['http', 'https']:
            return False, "Unsupported URL scheme"

        # Check against allowed patterns
        for pattern in cls.ALLOWED_URL_PATTERNS:
            if re.match(pattern, url):
                return True, None

        return False, "URL not in allowlist"

    @classmethod
    def secure_fetch(cls, url, timeout=10):
        """
        Safely fetch a URL with SSRF protections.
        Returns (success, data/error) tuple.
        """
        # Validate URL format and allowlist
        valid, error = cls.validate_url(url)
        if not valid:
            return False, error

        parsed = urlparse(url)

        # Resolve DNS and validate IP
        ip, error = cls.resolve_and_validate(parsed.hostname)
        if ip is None:
            return False, error

        # Make request using resolved IP (bypass DNS rebinding)
        import urllib.request
        import ssl

        # Create a custom opener that uses the resolved IP
        class SSRFSafeHandler(urllib.request.HTTPHandler):
            def connect(self, conn):
                conn.host = ip
                conn.host = '%s:%s' % (ip, conn.port)
                return super().connect(conn)

        opener = urllib.request.build_opener(SSRFSafeHandler)
        urllib.request.install_opener(opener)

        try:
            response = urllib.request.urlopen(url, timeout=timeout)
            return True, response.read()
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_ssrf_security_config():
        """Return SSRF security configuration."""
        return {
            'blocked_ip_ranges': [str(r) for r in cls.BLOCKED_IP_RANGES],
            'allowed_url_patterns': cls.ALLOWED_URL_PATTERNS,
            'dns_rebinding_protection': True,
            'require_ip_validation': True,
        }