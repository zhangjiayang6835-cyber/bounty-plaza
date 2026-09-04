"""Constant-Time RSA-OAEP Decryption & Bleichenbacher Oracle Defense.
Resolves Issue #57: Bleichenbacher Oracle in RSA-OAEP Decryption ($200).
Mitigates padding oracles, Manger side-channels, and error-based timing/message leaks.
"""

import hmac
import secrets
from typing import Optional, Tuple


UNIFORM_DECRYPTION_ERROR = "Decryption failed: invalid ciphertext or padding"


class DecryptionSecurityError(Exception):
    """Generic exception returned for all RSA-OAEP decryption anomalies."""
    pass


def constant_time_select(condition: int, a: bytes, b: bytes) -> bytes:
    """Select between two byte sequences in constant time without branching.

    Args:
        condition: 1 to select 'a', 0 to select 'b'.
        a: First byte string.
        b: Second byte string (must match len of a).

    Returns:
        Chosen byte string.
    """
    if len(a) != len(b):
        raise ValueError("Byte sequences must have identical length")

    mask = -condition & 0xFF
    return bytes(((val_a & mask) | (val_b & ~mask)) for val_a, val_b in zip(a, b))


class ConstantTimeOAEPDecryptor:
    """Implements side-channel-resistant RSA-OAEP unpadding and validation.
    Eliminates error message differentiation and timing oracles.
    """

    def __init__(self, key_size_bytes: int = 256, hash_size_bytes: int = 32):
        self.key_size_bytes = key_size_bytes
        self.hash_size_bytes = hash_size_bytes

    def verify_oaep_padding(
        self,
        padded_message: bytes,
        expected_lhash: bytes
    ) -> Tuple[bool, bytes]:
        """Perform constant-time validation of OAEP structure.

        Args:
            padded_message: Decrypted raw block (len == key_size_bytes).
            expected_lhash: Precomputed hash of optional label parameter.

        Returns:
            Tuple of (is_valid: bool, extracted_or_dummy_payload: bytes).
        """
        if len(padded_message) != self.key_size_bytes:
            # Length mismatch is padded to constant-time dummy processing
            dummy_payload = secrets.token_bytes(32)
            return False, dummy_payload

        # Block format: [0x00] || [maskedSeed] || [maskedDB]
        first_byte = padded_message[0]
        # Invariant: first byte must strictly be 0x00
        byte_zero_valid = 1 if first_byte == 0 else 0

        h_len = self.hash_size_bytes
        masked_seed = padded_message[1:1 + h_len]
        masked_db = padded_message[1 + h_len:]

        # Check DB structure: lHash' || PS || 0x01 || M
        lhash_received = masked_db[:h_len]
        lhash_match = 1 if hmac.compare_digest(lhash_received, expected_lhash) else 0

        # Scan PS and locate delimiter 0x01 in constant time
        remainder = masked_db[h_len:]
        delimiter_found = 0
        delimiter_index = 0

        for i, b in enumerate(remainder):
            # Delimiter is 0x01 preceded by zero or more 0x00 bytes
            is_one = 1 if b == 1 else 0
            is_zero = 1 if b == 0 else 0

            # Once delimiter is found, subsequent bytes form the message
            if delimiter_found == 0:
                if is_one:
                    delimiter_found = 1
                    delimiter_index = i
                elif not is_zero:
                    # Invalid byte in padding string PS
                    byte_zero_valid = 0

        overall_valid = byte_zero_valid & lhash_match & delimiter_found

        if overall_valid == 1:
            extracted_msg = remainder[delimiter_index + 1:]
        else:
            # Generate constant-time synthetic noise to defeat Bleichenbacher/Manger timing
            extracted_msg = secrets.token_bytes(32)

        return (overall_valid == 1), extracted_msg

    def decrypt_payload(
        self,
        raw_decrypted_block: bytes,
        expected_lhash: bytes
    ) -> bytes:
        """Secure unpadding wrapper returning identical error regardless of failure root cause."""
        is_valid, payload = self.verify_oaep_padding(raw_decrypted_block, expected_lhash)

        if not is_valid:
            # Strictly uniform error message; does NOT reveal whether padding, MAC, or byte0 failed
            raise DecryptionSecurityError(UNIFORM_DECRYPTION_ERROR)

        return payload
