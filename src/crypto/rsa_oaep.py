<content>
import os
import hashlib
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import utils
from cryptography.hazmat.primitives import constant_time

class RSAOAEPDecryptor:
    def __init__(self, private_key=None):
        if private_key is None:
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
        else:
            self.private_key = private_key

    def decrypt(self, ciphertext: bytes) -> bytes:
        """
        Decrypts the ciphertext using RSA-OAEP in a constant-time manner.
        Returns a unified error message for all decryption failures.
        """
        try:
            # Perform decryption
            plaintext = self.private_key.decrypt(
                ciphertext,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            return plaintext
        except Exception as e:
            # Return a unified error message for all decryption failures
            # This prevents information leakage through error messages
            return b"Decryption failed"

    def public_key_pem(self) -> str:
        """Returns the public key in PEM format"""
        public_key = self.private_key.public_key()
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem.decode('utf-8')

    def private_key_pem(self) -> str:
        """Returns the private key in PEM format"""
        pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )
        return pem.decode('utf-8')

    def verify_constant_time(self, plaintext1: bytes, plaintext2: bytes) -> bool:
        """
        Constant-time comparison function to prevent timing attacks.
        Returns True if the plaintexts are equal, False otherwise.
        """
        return constant_time.bytes_eq(plaintext1, plaintext2)

# Test vectors for Bleichenbacher attack validation
def generate_bleichenbacher_test_vectors():
    """Generate test vectors for Bleichenbacher attack validation"""
    decryptor = RSAOAEPDecryptor()
    
    # Valid ciphertext
    valid_plaintext = b"Hello, this is a secret message!"
    ciphertext = decryptor.private_key.encrypt(
        valid_plaintext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    
    # Invalid ciphertexts for testing
    invalid_ciphertexts = [
        # Modified valid ciphertext
        ciphertext[:-1] + bytes([ciphertext[-1] ^ 0x01]),
        # Completely random ciphertext
        os.urandom(256),
        # Ciphertext with wrong length
        ciphertext[:100] + ciphertext[150:],
        # Ciphertext with all zeros
        bytes(256),
    ]
    
    return {
        "valid_ciphertext": ciphertext,
        "valid_plaintext": valid_plaintext,
        "invalid_ciphertexts": invalid_ciphertexts
    }

# Example usage
if __name__ == "__main__":
    decryptor = RSAOAEPDecryptor()
    test_vectors = generate_bleichenbacher_test_vectors()
    
    # Test valid decryption
    decrypted = decryptor.decrypt(test_vectors["valid_ciphertext"])
    print(f"Valid decryption: {decrypted == test_vectors['valid_plaintext']}")
    
    # Test invalid decryptions (should all return the same error)
    for i, invalid_ct in enumerate(test_vectors["invalid_ciphertexts"]):
        error_msg = decryptor.decrypt(invalid_ct)
        print(f"Invalid ciphertext {i+1}: {error_msg}")
    
    # Test constant-time comparison
    print(f"Constant-time comparison (same): {decryptor.verify_constant_time(b'test', b'test')}")
    print(f"Constant-time comparison (different): {decryptor.verify_constant_time(b'test', 'tes')}")
</content>