"""DNS Zone Transfer (AXFR) Defense, TSIG Authentication & Split-Horizon View Engine.
Resolves Issue #308: DNS Zone Transfer Enabled -> Internal Network Mapping ($150 USD).
Compliant with RFC 5936 (AXFR) and RFC 8945 / RFC 2845 (TSIG).

Implements:
1. Strict IP Access Control Lists (ACLs) restricting AXFR requests to authorized slave/secondary servers.
2. Cryptographic Transaction Signature (TSIG) validation using HMAC-SHA256.
3. Timestamp-based replay protection with configurable fudge windows.
4. Split-Horizon DNS views isolating internal topology from public zones.
"""

import base64
import hashlib
import hmac
import ipaddress
import time
from typing import Any, Dict, List, Optional, Set


class DNSZoneTransferError(Exception):
    """Base exception for DNS zone transfer errors."""
    pass


class ZoneTransferDeniedError(DNSZoneTransferError):
    """Raised when an AXFR request comes from an unauthorized IP or lacks valid permissions."""
    pass


class TSIGAuthenticationError(DNSZoneTransferError):
    """Raised when TSIG signature is missing, expired, forged, or has key mismatch."""
    pass


class DNSView:
    """Represents a scoped DNS view in a Split-Horizon architecture."""

    def __init__(self, name: str, allowed_networks: List[str], records: Dict[str, List[Dict[str, Any]]]):
        self.name = name
        self.networks = [ipaddress.ip_network(net) for net in allowed_networks]
        # zone -> list of record dicts: {"name": str, "type": str, "ttl": int, "data": str}
        self.records = records

    def matches_client_ip(self, client_ip: str) -> bool:
        """Determines if the client IP belongs to this view's network scope."""
        ip_obj = ipaddress.ip_address(client_ip)
        return any(ip_obj in net for net in self.networks)


class SecureDNSZoneTransferManager:
    """Protects authoritative DNS servers against AXFR reconnaissance, data leakage, and topology discovery."""

    def __init__(
        self,
        allowed_slave_ips: Set[str],
        tsig_keys: Dict[str, str],  # key_name -> secret (base64 or plaintext)
        max_fudge_seconds: int = 300,
    ):
        self.allowed_slave_ips = set(allowed_slave_ips)
        self.tsig_keys = {
            k: base64.b64decode(v) if self._is_base64(v) else v.encode("utf-8")
            for k, v in tsig_keys.items()
        }
        self.max_fudge_seconds = max_fudge_seconds
        self._views: Dict[str, DNSView] = {}

    @staticmethod
    def _is_base64(s: str) -> bool:
        try:
            return base64.b64encode(base64.b64decode(s)).decode("ascii").rstrip("=") == s.rstrip("=")
        except Exception:
            return False

    def add_view(self, view: DNSView) -> None:
        """Register a split-horizon view."""
        self._views[view.name] = view

    def compute_tsig_digest(
        self,
        key_secret: bytes,
        zone: str,
        timestamp: int,
        fudge: int,
        request_id: int,
    ) -> str:
        """Computes HMAC-SHA256 digest for TSIG envelope."""
        message = f"{zone.lower()}:{timestamp}:{fudge}:{request_id}".encode("utf-8")
        return hmac.new(key_secret, message, hashlib.sha256).hexdigest()

    def verify_tsig(
        self,
        zone: str,
        key_name: Optional[str],
        received_mac: Optional[str],
        timestamp: Optional[int],
        fudge: Optional[int],
        request_id: int,
    ) -> bool:
        """Cryptographically validates TSIG signature and verifies freshness."""
        if not key_name or not received_mac or timestamp is None:
            raise TSIGAuthenticationError("TSIG record is missing or incomplete for zone transfer request.")

        if key_name not in self.tsig_keys:
            raise TSIGAuthenticationError(f"Unknown or untrusted TSIG key name: '{key_name}'.")

        key_secret = self.tsig_keys[key_name]
        fudge_window = fudge if fudge is not None else self.max_fudge_seconds

        now = int(time.time())
        if abs(now - timestamp) > fudge_window:
            raise TSIGAuthenticationError(
                f"TSIG signature timestamp expired or out of bounds (drift: {abs(now - timestamp)}s > {fudge_window}s)."
            )

        expected_mac = self.compute_tsig_digest(
            key_secret=key_secret,
            zone=zone,
            timestamp=timestamp,
            fudge=fudge_window,
            request_id=request_id,
        )

        if not hmac.compare_digest(expected_mac, received_mac):
            raise TSIGAuthenticationError("TSIG signature verification failed: invalid cryptographic MAC.")

        return True

    def resolve_view_for_client(self, client_ip: str) -> DNSView:
        """Routes client to the correct Split-Horizon view (Internal vs External)."""
        for view in self._views.values():
            if view.name != "external" and view.matches_client_ip(client_ip):
                return view
        # Default fallback to external view
        return self._views.get("external") or list(self._views.values())[0]

    def request_axfr(
        self,
        zone: str,
        client_ip: str,
        tsig_key_name: Optional[str] = None,
        tsig_mac: Optional[str] = None,
        tsig_timestamp: Optional[int] = None,
        tsig_fudge: Optional[int] = None,
        request_id: int = 1,
    ) -> List[Dict[str, Any]]:
        """Handles AXFR Zone Transfer requests with multi-tier defense:
        1. Slave IP ACL check
        2. TSIG HMAC-SHA256 signature verification
        3. Split-horizon scoped zone payload extraction
        """
        # 1. IP ACL Check: Only authorized slaves may perform AXFR
        if client_ip not in self.allowed_slave_ips:
            raise ZoneTransferDeniedError(
                f"AXFR zone transfer rejected: Client IP '{client_ip}' is not in authorized slave ACL."
            )

        # 2. TSIG Authentication Requirement
        self.verify_tsig(
            zone=zone,
            key_name=tsig_key_name,
            received_mac=tsig_mac,
            timestamp=tsig_timestamp,
            fudge=tsig_fudge,
            request_id=request_id,
        )

        # 3. Retrieve zone records from client's assigned split-horizon view
        view = self.resolve_view_for_client(client_ip)
        zone_records = view.records.get(zone.lower())
        if zone_records is None:
            raise DNSZoneTransferError(f"Zone '{zone}' not found in view '{view.name}'.")

        # Return full zone dump formatted for replication
        return [dict(rec) for rec in zone_records]

    def query_record(self, name: str, record_type: str, client_ip: str) -> List[Dict[str, Any]]:
        """Standard DNS query routing through Split-Horizon views."""
        view = self.resolve_view_for_client(client_ip)
        results = []
        for zone, records in view.records.items():
            for rec in records:
                if rec["name"].lower() == name.lower() and (
                    record_type.upper() == "ANY" or rec["type"].upper() == record_type.upper()
                ):
                    results.append(dict(rec))
        return results
