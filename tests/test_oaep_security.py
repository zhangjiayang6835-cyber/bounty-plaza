import hashlib
import secrets
import pytest
from scripts.oaep_security import (
    ConstantTimeOAEPDecryptor,
    DecryptionSecurityError,
    UNIFORM_DECRYPTION_ERROR,
    constant_time_select,
)


def build_mock_oaep_block(key_size=256, hash_size=32, message=b"secret_key_123"):
    lhash = hashlib.sha256(b"").digest()
    ps = b"\x00" * 10
    db = lhash + ps + b"\x01" + message
    # Pad to total key size - 1 - hash_size
    pad_needed = (key_size - 1 - hash_size) - len(db)
    if pad_needed > 0:
        db = lhash + (b"\x00" * (10 + pad_needed)) + b"\x01" + message
    seed = secrets.token_bytes(hash_size)
    block = b"\x00" + seed + db
    return block, lhash


def test_constant_time_select():
    a = b"AAAA"
    b = b"BBBB"
    assert constant_time_select(1, a, b) == a
    assert constant_time_select(0, a, b) == b


def test_oaep_decryptor_valid_block():
    decryptor = ConstantTimeOAEPDecryptor(key_size_bytes=256, hash_size_bytes=32)
    block, lhash = build_mock_oaep_block(message=b"super_secret_token_42")
    payload = decryptor.decrypt_payload(block, lhash)
    assert payload == b"super_secret_token_42"


def test_oaep_decryptor_uniform_error_on_corrupt_first_byte():
    decryptor = ConstantTimeOAEPDecryptor(key_size_bytes=256, hash_size_bytes=32)
    block, lhash = build_mock_oaep_block()
    corrupt_block = b"\x01" + block[1:]

    with pytest.raises(DecryptionSecurityError) as excinfo:
        decryptor.decrypt_payload(corrupt_block, lhash)
    assert str(excinfo.value) == UNIFORM_DECRYPTION_ERROR


def test_oaep_decryptor_uniform_error_on_corrupt_lhash():
    decryptor = ConstantTimeOAEPDecryptor(key_size_bytes=256, hash_size_bytes=32)
    block, lhash = build_mock_oaep_block()
    wrong_lhash = hashlib.sha256(b"wrong_label").digest()

    with pytest.raises(DecryptionSecurityError) as excinfo:
        decryptor.decrypt_payload(block, wrong_lhash)
    assert str(excinfo.value) == UNIFORM_DECRYPTION_ERROR


def test_oaep_decryptor_uniform_error_on_corrupt_delimiter():
    decryptor = ConstantTimeOAEPDecryptor(key_size_bytes=256, hash_size_bytes=32)
    block, lhash = build_mock_oaep_block()
    # Replace all bytes with 0x00 so no 0x01 delimiter exists
    corrupt_block = block[:33] + (b"\x00" * (256 - 33))

    with pytest.raises(DecryptionSecurityError) as excinfo:
        decryptor.decrypt_payload(corrupt_block, lhash)
    assert str(excinfo.value) == UNIFORM_DECRYPTION_ERROR
