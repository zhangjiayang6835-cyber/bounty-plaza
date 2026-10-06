"""Unit and security test suite for Safe Cache Serialization & Pickle RCE Neutralization.
Resolves Issue #302: Python Pickle Deserialization RCE via Cache ($200 USD).
"""

import pickle
import time
import pytest
from scripts.safe_cache_serializer import (
    SafeCacheSerializer,
    DeserializationSecurityError,
    SignatureVerificationError,
    CacheExpiredError,
)


@pytest.fixture
def serializer():
    return SafeCacheSerializer(signing_key="ultra_secure_cache_signing_key_302", default_ttl_seconds=300)


def test_roundtrip_serialization_data_structures(serializer):
    sample_data = {
        "user_id": "usr_9988",
        "roles": ["editor", "billing"],
        "preferences": {"dark_mode": True, "currency": "USD"},
        "balance": 1500.25,
    }
    encoded = serializer.dumps(sample_data)
    decoded = serializer.loads(encoded)
    assert decoded == sample_data


def test_raw_pickle_stream_rejection(serializer):
    """Malicious actor attempting to pass raw pickle stream."""
    malicious_pickle = pickle.dumps({"admin": True})
    with pytest.raises(DeserializationSecurityError, match="Malicious pickle bytecode detected"):
        serializer.loads(malicious_pickle)


def test_signature_tampering_rejected(serializer):
    """Attacker attempts to tamper with payload in cache without valid secret key."""
    data = {"role": "user", "credits": 10}
    encoded = serializer.dumps(data)

    # Tamper with payload
    import json
    envelope = json.loads(encoded)
    # Alter payload base64 to elevate permissions
    import base64
    tampered_bytes = json.dumps({"role": "admin", "credits": 99999}).encode("utf-8")
    envelope["payload_b64"] = base64.b64encode(tampered_bytes).decode("ascii")
    tampered_envelope = json.dumps(envelope)

    with pytest.raises(SignatureVerificationError, match="Cache payload has been tampered with"):
        serializer.loads(tampered_envelope)


def test_cache_ttl_expiration(serializer):
    """Verify expired cache payloads are rejected."""
    short_serializer = SafeCacheSerializer(signing_key="test_key", default_ttl_seconds=1)
    data = {"session_token": "abc_xyz"}
    encoded = short_serializer.dumps(data, ttl_seconds=1)

    time.sleep(1.2)
    with pytest.raises(CacheExpiredError, match="Cache payload expired"):
        short_serializer.loads(encoded)


def test_non_json_serializable_object_rejected(serializer):
    """Objects that cannot be safely serialized to JSON fail fast."""
    class CustomObject:
        pass

    with pytest.raises(DeserializationSecurityError, match="not JSON-serializable"):
        serializer.dumps(CustomObject())


def test_malformed_envelope_rejected(serializer):
    with pytest.raises(DeserializationSecurityError, match="Invalid JSON envelope"):
        serializer.loads("not_a_json_envelope")

    with pytest.raises(DeserializationSecurityError, match="Envelope must be a JSON dictionary"):
        serializer.loads("[1, 2, 3]")
