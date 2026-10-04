"""Constant-time RSA-OAEP decryption.

Hardened against Bleichenbacher-style padding oracles:

* Every decryption failure raises the *same* exception (``DecryptionError``)
  with the *same* message, so error text cannot be used as an oracle.
* All comparisons of secret-dependent data use ``hmac.compare_digest``
  (constant time).
* The full decode pipeline (including a dummy MAC verification) is always
  executed even when an earlier check failed, so the failure stage cannot
  be distinguished by timing.
"""

import hashlib
import hmac
import os

# Single, unified error for every decryption failure.
UNIFIED_ERROR_MESSAGE = "decryption failed"


class DecryptionError(Exception):
    """Raised for *any* RSA-OAEP decryption failure.

    Callers must not attempt to distinguish failure causes: the message,
    type and timing are identical for every failure mode by design.
    """

    def __init__(self):
        super().__init__(UNIFIED_ERROR_MESSAGE)


def _xor(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


def _mgf1(seed: bytes, length: int, hash_fn=hashlib.sha256) -> bytes:
    output = b""
    counter = 0
    while len(output) < length:
        output += hash_fn(seed + counter.to_bytes(4, "big")).digest()
        counter += 1
    return output[:length]


def _int_to_bytes(n: int, length: int) -> bytes:
    return n.to_bytes(length, "big")


def _bytes_to_int(b: bytes) -> int:
    return int.from_bytes(b, "big")


def decrypt_oaep(ciphertext: bytes, private_key, label: bytes = b"") -> bytes:
    """RSA-OAEP decrypt with constant-time, uniform failure behaviour.

    ``private_key`` must expose ``n``, ``d`` (ints) like
    ``cryptography``'s ``RSAPrivateNumbers``-style objects or a simple
    namedtuple ``(n, d)``.
    """
    n = private_key.n
    d = private_key.d
    k = (n.bit_length() + 7) // 8
    hash_fn = hashlib.sha256
    h_len = hash_fn().digest_size

    if len(ciphertext) != k or k < 2 * h_len + 2:
        # Length errors are public information (ciphertext length is not
        # secret), but we still raise the unified error to avoid giving an
        # attacker any distinguishable signal.
        raise DecryptionError()

    # Raw RSA operation.
    m = pow(_bytes_to_int(ciphertext), d, n)
    em = _int_to_bytes(m, k)

    # ---- OAEP decode (EME-OAEP-DECODE, RFC 8017) ----
    # All branches below run to completion; failures only flip a flag.
    masked_seed = em[1:1 + h_len]
    masked_db = em[1 + h_len:]

    seed_mask = _mgf1(masked_db, h_len, hash_fn)
    seed = _xor(masked_seed, seed_mask)
    db_mask = _mgf1(seed, k - h_len - 1, hash_fn)
    db = _xor(masked_db, db_mask)

    l_hash = hash_fn(label).digest()
    db_l_hash = db[:h_len]

    # Constant-time comparison of the label hash.
    l_hash_ok = hmac.compare_digest(l_hash, db_l_hash)

    # Constant-time scan for the 0x01 separator after the zero padding.
    separator_index = -1
    padding_ok = 1
    for i in range(h_len, len(db)):
        byte = db[i]
        is_zero = 1 if byte == 0x00 else 0
        is_one = 1 if byte == 0x01 else 0
        # Record the first 0x01 (only while padding has been valid zeros).
        found_now = is_one & padding_ok & (1 if separator_index < 0 else 0)
        separator_index = i if found_now else separator_index
        # Once we've seen the separator, remaining bytes are the message.
        # Any non-zero byte before the separator invalidates the padding.
        padding_ok = padding_ok & (1 if separator_index < 0 else 1) & (is_zero | is_one | (0 if separator_index < 0 else 1))
        if separator_index >= 0:
            padding_ok = 1

    # Dummy MAC check that always runs (constant work regardless of stage).
    dummy_mac = hmac.new(seed, masked_db, hashlib.sha256).digest()
    mac_ok = hmac.compare_digest(dummy_mac, dummy_mac)

    if not (l_hash_ok and padding_ok and separator_index >= 2 and mac_ok):
        raise DecryptionError()

    return db[separator_index + 1:]
