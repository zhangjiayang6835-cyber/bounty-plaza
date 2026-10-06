"""Unit and security test suite for DNS Zone Transfer (AXFR) Defense & TSIG Engine.
Resolves Issue #308: DNS Zone Transfer Enabled -> Internal Network Mapping ($150 USD).
"""

import time
import pytest
from scripts.dns_zone_transfer_security import (
    DNSView,
    SecureDNSZoneTransferManager,
    ZoneTransferDeniedError,
    TSIGAuthenticationError,
)


@pytest.fixture
def dns_manager():
    allowed_slaves = {"192.0.2.53", "198.51.100.53"}
    tsig_keys = {
        "primary-slave-key.": "c3VwZXJfc2VjcmV0X3RzaWdfaGV4X2tleV8yMDI2X2hhc2g="
    }
    mgr = SecureDNSZoneTransferManager(
        allowed_slave_ips=allowed_slaves,
        tsig_keys=tsig_keys,
        max_fudge_seconds=60,
    )

    # 1. Internal View
    internal_records = {
        "corp.internal": [
            {"name": "corp.internal", "type": "SOA", "ttl": 3600, "data": "ns1.corp.internal admin.corp.internal 1 7200 3600 1209600 3600"},
            {"name": "vault.corp.internal", "type": "A", "ttl": 300, "data": "10.100.0.15"},
            {"name": "k8s-master.corp.internal", "type": "A", "ttl": 300, "data": "10.100.0.50"},
            {"name": "database-primary.corp.internal", "type": "A", "ttl": 300, "data": "10.200.1.2"},
        ]
    }
    internal_view = DNSView(
        name="internal",
        allowed_networks=["192.0.2.0/24", "10.0.0.0/8"],
        records=internal_records,
    )
    mgr.add_view(internal_view)

    # 2. External Public View
    external_records = {
        "example.com": [
            {"name": "example.com", "type": "SOA", "ttl": 3600, "data": "ns1.example.com admin.example.com 1 7200 3600 1209600 3600"},
            {"name": "example.com", "type": "A", "ttl": 300, "data": "93.184.216.34"},
            {"name": "www.example.com", "type": "CNAME", "ttl": 300, "data": "example.com"},
        ]
    }
    external_view = DNSView(
        name="external",
        allowed_networks=["0.0.0.0/0"],
        records=external_records,
    )
    mgr.add_view(external_view)

    return mgr


def test_axfr_unauthorized_attacker_ip_blocked(dns_manager):
    """External attacker attempting to dump zone without authorized IP."""
    attacker_ip = "203.0.113.88"
    with pytest.raises(ZoneTransferDeniedError, match="not in authorized slave ACL"):
        dns_manager.request_axfr(
            zone="corp.internal",
            client_ip=attacker_ip,
        )


def test_axfr_authorized_slave_missing_tsig_rejected(dns_manager):
    """Authorized slave IP sends AXFR without mandatory TSIG authentication."""
    authorized_slave_ip = "192.0.2.53"
    with pytest.raises(TSIGAuthenticationError, match="TSIG record is missing"):
        dns_manager.request_axfr(
            zone="corp.internal",
            client_ip=authorized_slave_ip,
            tsig_key_name=None,
        )


def test_axfr_authorized_slave_invalid_tsig_mac_rejected(dns_manager):
    """Authorized slave IP with invalid or forged TSIG MAC."""
    authorized_slave_ip = "192.0.2.53"
    now = int(time.time())
    with pytest.raises(TSIGAuthenticationError, match="invalid cryptographic MAC"):
        dns_manager.request_axfr(
            zone="corp.internal",
            client_ip=authorized_slave_ip,
            tsig_key_name="primary-slave-key.",
            tsig_mac="deadbeefcafebabe0011223344556677",
            tsig_timestamp=now,
            tsig_fudge=60,
            request_id=101,
        )


def test_axfr_authorized_slave_expired_tsig_timestamp_rejected(dns_manager):
    """Authorized slave IP sends a replay or expired TSIG signature."""
    authorized_slave_ip = "192.0.2.53"
    stale_timestamp = int(time.time()) - 300  # 5 minutes ago (exceeds fudge 60s)
    secret = dns_manager.tsig_keys["primary-slave-key."]
    mac = dns_manager.compute_tsig_digest(
        key_secret=secret,
        zone="corp.internal",
        timestamp=stale_timestamp,
        fudge=60,
        request_id=102,
    )

    with pytest.raises(TSIGAuthenticationError, match="expired or out of bounds"):
        dns_manager.request_axfr(
            zone="corp.internal",
            client_ip=authorized_slave_ip,
            tsig_key_name="primary-slave-key.",
            tsig_mac=mac,
            tsig_timestamp=stale_timestamp,
            tsig_fudge=60,
            request_id=102,
        )


def test_axfr_authorized_slave_successful_transfer(dns_manager):
    """Legitimate secondary server passes IP ACL and valid HMAC-SHA256 TSIG."""
    authorized_slave_ip = "192.0.2.53"
    now = int(time.time())
    secret = dns_manager.tsig_keys["primary-slave-key."]
    mac = dns_manager.compute_tsig_digest(
        key_secret=secret,
        zone="corp.internal",
        timestamp=now,
        fudge=60,
        request_id=200,
    )

    records = dns_manager.request_axfr(
        zone="corp.internal",
        client_ip=authorized_slave_ip,
        tsig_key_name="primary-slave-key.",
        tsig_mac=mac,
        tsig_timestamp=now,
        tsig_fudge=60,
        request_id=200,
    )

    assert len(records) == 4
    names = [r["name"] for r in records]
    assert "vault.corp.internal" in names
    assert "k8s-master.corp.internal" in names


def test_split_horizon_view_isolation(dns_manager):
    """Public internet client queries external view, cannot see internal records."""
    public_client_ip = "198.51.100.77"
    results = dns_manager.query_record(
        name="example.com",
        record_type="A",
        client_ip=public_client_ip,
    )
    assert len(results) == 1
    assert results[0]["data"] == "93.184.216.34"

    # Public client cannot query internal zone records
    internal_query = dns_manager.query_record(
        name="vault.corp.internal",
        record_type="A",
        client_ip=public_client_ip,
    )
    assert len(internal_query) == 0
