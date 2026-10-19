# fix_pickle_rce.py
import json
import hmac
import hashlib
import base64
import secrets

class PickleRCEProtection:
    """Protect against pickle deserialization RCE by using safe serialization."""

    SECRET_KEY = secrets.token_hex(32)

    @staticmethod
    def serialize_safe(data):
        """
        Safely serialize data using JSON instead of pickle.
        Returns a JSON string with HMAC signature.
        """
        json_str = json.dumps(data, default=str)
        signature = PickleRCEProtection.sign(json_str)
        return json.dumps({
            'data': json_str,
            'signature': signature,
        })

    @staticmethod
    def deserialize_safe(serialized):
        """
        Safely deserialize data, verifying the HMAC signature.
        Raises ValueError if signature is invalid.
        """
        if not isinstance(serialized, str):
            raise ValueError("Invalid serialized data format")

        try:
            envelope = json.loads(serialized)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format")

        data_str = envelope.get('data')
        signature = envelope.get('signature')

        if not data_str or not signature:
            raise ValueError("Missing data or signature")

        # Verify signature
        if not PickleRCEProtection.verify_signature(data_str, signature):
            raise ValueError("Invalid signature - possible tampering")

        return json.loads(data_str)

    @staticmethod
    def sign(data):
        """Generate HMAC signature for data."""
        return hmac.new(
            PickleRCEProtection.SECRET_KEY.encode(),
            data.encode(),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def verify_signature(data, signature):
        """Verify HMAC signature using constant-time comparison."""
        expected = PickleRCEProtection.sign(data)
        return hmac.compare_digest(signature, expected)

    @staticmethod
    def is_pickle_payload(data):
        """Detect if data appears to be a pickle payload."""
        pickle_markers = [b'\x80', b'\x94', b'\x95', b'c', b'S', b't', b'(']
        if isinstance(data, bytes):
            # Check if starts with pickle protocol marker
            if len(data) > 0 and data[0] in [0x80, 0x94, 0x95]:
                return True
        return False

    @staticmethod
    def safe_cache_get(cache_key, cache_data):
        """Safely retrieve data from cache."""
        if PickleRCEProtection.is_pickle_payload(cache_data):
            raise ValueError("Pickle payload detected in cache - refusing to deserialize")
        return PickleRCEProtection.deserialize_safe(cache_data)

    @staticmethod
    def safe_cache_set(cache_key, data):
        """Safely store data in cache."""
        return PickleRCEProtection.serialize_safe(data)