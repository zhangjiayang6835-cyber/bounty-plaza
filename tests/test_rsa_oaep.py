<content>
import unittest
from src.crypto.rsa_oaep import RSAOAEPDecryptor, generate_bleichenbacher_test_vectors

class TestRSAOAEP(unittest.TestCase):
    def setUp(self):
        self.decryptor = RSAOAEPDecryptor()
        self.test_vectors = generate_bleichenbacher_test_vectors()

    def test_valid_decryption(self):
        """Test that valid ciphertexts are properly decrypted"""
        decrypted = self.decryptor.decrypt(self.test_vectors["valid_ciphertext"])
        self.assertEqual(decrypted, self.test_vectors["valid_plaintext"])

    def test_invalid_decryption_unified_error(self):
        """Test that all invalid decryptions return the same error message"""
        error_message = b"Decryption failed"
        for invalid_ct in self.test_vectors["invalid_ciphertexts"]:
            decrypted = self.decryptor.decrypt(invalid_ct)
            self.assertEqual(decrypted, error_message)

    def test_constant_time_comparison(self):
        """Test the constant-time comparison function"""
        # Test with equal inputs
        self.assertTrue(self.decryptor.verify_constant_time(b"test", b"test"))
        
        # Test with different inputs
        self.assertFalse(self.decryptor.verify_constant_time(b"test", b"tes"))
        self.assertFalse(self.decryptor.verify_constant_time(b"test", b"test "))
        
        # Test with inputs of different lengths (should return False)
        self.assertFalse(self.decryptor.verify_constant_time(b"test", b"testing"))

    def test_bleichenbacher_resistance(self):
        """
        Test that the implementation is resistant to Bleichenbacher attacks.
        This is a basic test - in a real scenario, more sophisticated tests would be needed.
        """
        # Get the public key
        public_key_pem = self.decryptor.public_key_pem()
        
        # Test that all invalid ciphertexts produce the same error
        errors = []
        for invalid_ct in self.test_vectors["invalid_ciphertexts"]:
            errors.append(self.decryptor.decrypt(invalid_ct))
        
        # All errors should be identical
        self.assertTrue(all(e == errors[0] for e in errors))

    def test_public_key_format(self):
        """Test that the public key is in the correct PEM format"""
        public_key_pem = self.decryptor.public_key_pem()
        self.assertTrue(public_key_pem.startswith("-----BEGIN PUBLIC KEY-----"))
        self.assertTrue(public_key_pem.endswith("-----END PUBLIC KEY-----"))

if __name__ == "__main__":
    unittest.main()
</content>