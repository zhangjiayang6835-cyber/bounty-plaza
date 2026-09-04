"""Unit test suite for NFH Wake Holder Gate Vulnerability Audit and Hardening.
Tests Issue #882 requirements:
- Reproduction of transfer race condition bypass on unmodified Wake Gate logic.
- Canonical endpoint URL parsing and strict hostname/scheme verification.
- Address normalization and case-folding defense.
- Monotonic timestamp freshness and transfer race defense in hardened gate.
"""

import pytest
import time
from scripts.nfh_wake_audit import (
    AgentPresenceHeartbeat,
    TokenState,
    VulnerableNFHWakeGate,
    HardenedNFHWakeGate,
)


def test_vulnerability_reproduction_transfer_race():
    """Reproduces the flaw where an ex-owner's stale heartbeat emitted within TTL

    succeeds even after the token was transferred to a new owner, if heartbeat.timestamp
    is not validated against token.last_transferred_at.
    """
    now = 1757000000.0
    alice = "0x1111111111111111111111111111111111111111"
    bob = "0x2222222222222222222222222222222222222222"

    # Alice owned token 42 and signed a heartbeat at t=0
    heartbeat_alice = AgentPresenceHeartbeat(
        token_id=42,
        signer_address=alice,
        timestamp=now - 30.0,  # 30 seconds ago
        nonce=101,
        signature="0xabcdef1234567890",
    )

    # 10 seconds ago, token was transferred to Bob!
    token = TokenState(
        token_id=42,
        current_owner=bob,
        last_transferred_at=now - 10.0,
    )

    # If the token owner was checked at time of signing or if attacker queries with Alice's address state
    token_stale_view = TokenState(
        token_id=42,
        current_owner=alice,
        last_transferred_at=now - 10.0,  # Transfer happened AFTER Alice signed heartbeat!
    )

    # On the unmodified logic, because heartbeat_age (30s) <= TTL (300s) and signer == owner:
    vulnerable_res = VulnerableNFHWakeGate.verify_and_emit_receipt(
        endpoint_url="https://api.notforhumans.fun/v1/wake",
        token=token_stale_view,
        heartbeat=heartbeat_alice,
        current_time=now,
    )
    # The unmodified gate issues HOLDER_VERIFIED_AT_WAKE even though Alice transferred it!
    assert vulnerable_res["status"] == "HOLDER_VERIFIED_AT_WAKE"

    # In the Hardened gate, the transfer race defense catches this immediately:
    hardened_res = HardenedNFHWakeGate.verify_and_emit_receipt(
        endpoint_url="https://api.notforhumans.fun/v1/wake",
        token=token_stale_view,
        heartbeat=heartbeat_alice,
        current_time=now,
    )
    assert hardened_res["status"] == "REJECTED"
    assert "TRANSFER_RACE_DETECTED" in hardened_res["reason"]


def test_canonical_endpoint_validation():
    now = 1757000000.0
    alice = "0x1111111111111111111111111111111111111111"
    token = TokenState(token_id=42, current_owner=alice, last_transferred_at=now - 500.0)
    heartbeat = AgentPresenceHeartbeat(
        token_id=42,
        signer_address=alice,
        timestamp=now - 10.0,
        nonce=1,
        signature="0xsig",
    )

    # Spoofed domain that starts with prefix
    spoofed_endpoint = "https://api.notforhumans.fun.attacker.com/v1/wake"
    res = HardenedNFHWakeGate.verify_and_emit_receipt(
        endpoint_url=spoofed_endpoint,
        token=token,
        heartbeat=heartbeat,
        current_time=now,
    )
    assert res["status"] == "REJECTED"
    assert res["reason"] == "CANONICAL_ENDPOINT_VALIDATION_FAILED"

    # Valid canonical endpoint
    valid_res = HardenedNFHWakeGate.verify_and_emit_receipt(
        endpoint_url="https://api.notforhumans.fun/v1/wake",
        token=token,
        heartbeat=heartbeat,
        current_time=now,
    )
    assert valid_res["status"] == "HOLDER_VERIFIED_AT_WAKE"


def test_address_checksum_and_case_normalization():
    now = 1757000000.0
    lower_addr = "0x5aaeb6053f3e94c9b9a09f33669435e7ef1beaed"
    checksum_addr = "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed"

    token = TokenState(token_id=1, current_owner=checksum_addr, last_transferred_at=now - 200.0)
    heartbeat = AgentPresenceHeartbeat(
        token_id=1,
        signer_address=lower_addr,
        timestamp=now - 5.0,
        nonce=2,
        signature="0xsig",
    )

    res = HardenedNFHWakeGate.verify_and_emit_receipt(
        endpoint_url="https://api.notforhumans.fun/v1/wake",
        token=token,
        heartbeat=heartbeat,
        current_time=now,
    )
    assert res["status"] == "HOLDER_VERIFIED_AT_WAKE"
    assert res["owner"] == lower_addr


def test_heartbeat_freshness_window_tightened():
    now = 1757000000.0
    owner = "0x3333333333333333333333333333333333333333"
    token = TokenState(token_id=5, current_owner=owner, last_transferred_at=now - 1000.0)

    # 75 seconds old heartbeat (> 60s max TTL in hardened gate)
    stale_heartbeat = AgentPresenceHeartbeat(
        token_id=5,
        signer_address=owner,
        timestamp=now - 75.0,
        nonce=3,
        signature="0xsig",
    )

    res = HardenedNFHWakeGate.verify_and_emit_receipt(
        endpoint_url="https://api.notforhumans.fun/v1/wake",
        token=token,
        heartbeat=stale_heartbeat,
        current_time=now,
    )
    assert res["status"] == "REJECTED"
    assert "HEARTBEAT_EXPIRED" in res["reason"]
