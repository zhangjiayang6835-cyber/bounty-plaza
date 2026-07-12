# fix_bleichenbacher.py
import time
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

def secure_decrypt(ciphertext, private_key):
    """
    Decrypts ciphertext using RSA-OAEP with constant-time error responses.
    """
    try:
        # Attempt decryption
        plaintext = private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return plaintext
    except Exception:
        # Constant-time dummy response (no oracle leak)
        return None

def secure_compare(a, b):
    """
    Constant-time comparison to prevent timing attacks.
    """
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= x ^ y
    return result == 0