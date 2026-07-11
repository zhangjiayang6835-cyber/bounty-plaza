# fix_dns_zone_transfer.py
"""
DNS Zone Transfer Protection - Disable AXFR or restrict to authorized servers.

Configuration for BIND/named.conf:
```
options {
    allow-transfer { none; };  // Disable zone transfer by default
    allow-query { localhost; 10.0.0.0/8; };  // Restrict queries
};

// If zone transfer is needed for secondary servers:
zone "example.com" IN {
    type master;
    file "db.example.com";
    allow-transfer { 10.0.0.2; };  // Only secondary DNS server
    allow-notify { 10.0.0.2; };
    also-notify { 10.0.0.2; };
};
```
"""

class DNSZoneTransferProtection:
    """Protect against unauthorized DNS zone transfers."""

    # Authorized secondary DNS servers for zone transfer
    AUTHORIZED_SECONDARIES = [
        '10.0.0.2',   # Secondary DNS server
        '10.0.0.3',   # Backup DNS server
    ]

    @classmethod
    def get_bind_config(cls):
        """Return secure BIND configuration with zone transfer disabled."""
        config = """
options {
    directory \"/var/named\";
    allow-query { localhost; 10.0.0.0/8; };
    allow-transfer { none; };
    version \"\";
    recursion yes;
    dnssec-validation auto;
};

logging {
    category xfer-in { zone_xfer_log; };
    category xfer-out { zone_xfer_log; };
    channel zone_xfer_log {
        file \"/var/log/named/xfer.log\" versions 10 size 100M;
        severity info;
        print-time yes;
        print-category yes;
    };
};
"""
        return config

    @classmethod
    def check_zone_transfer_request(cls, client_ip, zone):
        """
        Check if a zone transfer request from client_ip is authorized.
        Returns (allowed, reason) tuple.
        """
        if client_ip in cls.AUTHORIZED_SECONDARIES:
            return True, None

        # Log the unauthorized attempt
        cls.log_zone_transfer_attempt(client_ip, zone)
        return False, "Zone transfer not authorized from %s" % client_ip

    @staticmethod
    def log_zone_transfer_attempt(client_ip, zone):
        """Log unauthorized zone transfer attempts."""
        import datetime
        log_entry = (
            "%s - WARNING: Unauthorized zone transfer attempt "
            "from %s for zone %s"
        ) % (datetime.datetime.utcnow().isoformat(), client_ip, zone)
        print(log_entry)

    @staticmethod
    def is_axfr_request(message):
        """Check if a DNS message is an AXFR request."""
        # AXFR = opcode 0, type 252
        return getattr(message, 'opcode', 0) == 0 and getattr(message, 'qr', 1) == 0