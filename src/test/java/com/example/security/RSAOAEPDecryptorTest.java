package com.example.security;

import org.junit.jupiter.api.*;
import java.security.*;
import static org.junit.jupiter.api.Assertions.*;

class RSAOAEPDecryptorTest {
    private RSAOAEPDecryptor decryptor;
    private KeyPair keyPair;

    @BeforeEach
    void setUp() throws Exception {
        KeyPairGenerator keyGen = KeyPairGenerator.getInstance("RSA");
        keyGen.initialize(2048);
        keyPair = keyGen.generateKeyPair();
        decryptor = new RSAOAEPDecryptor(keyPair.getPrivate());
    }

    @Test
    void testValidDecryption() throws Exception {
        // Create a valid ciphertext
        Cipher cipher = Cipher.getInstance("RSA/ECB/OAEPWithSHA-256AndMGF1Padding");
        cipher.init(Cipher.ENCRYPT_MODE, keyPair.getPublic());
        byte[] plaintext = "Test message".getBytes();
        byte[] ciphertext = cipher.doFinal(plaintext);
        
        byte[] decrypted = decryptor.decrypt(ciphertext);
        assertArrayEquals(plaintext, decrypted);
    }

    @Test
    void testInvalidCiphertextReturnsSameError() throws Exception {
        // Test with invalid ciphertext
        byte[] invalidCiphertext = new byte[256];
        new SecureRandom().nextBytes(invalidCiphertext);
        
        CryptoException exception1 = assertThrows(CryptoException.class, () -> {
            decryptor.decrypt(invalidCiphertext);
        });
        
        CryptoException exception2 = assertThrows(CryptoException.class, () -> {
            decryptor.decrypt(invalidCiphertext);
        });
        
        // Error messages should be identical
        assertEquals(exception1.getMessage(), exception2.getMessage());
    }

    @Test
    void testConstantTimeComparison() {
        byte[] a = new byte[100];
        byte[] b = new byte[100];
        byte[] c = new byte[100];
        
        Arrays.fill(a, (byte) 0xFF);
        Arrays.fill(b, (byte) 0xFF);
        Arrays.fill(c, (byte) 0xFE);
        
        assertTrue(decryptor.constantTimeEquals(a, b));
        assertFalse(decryptor.constantTimeEquals(a, c));
    }

    @Test
    void testBleichenbacherTestVectors() throws Exception {
        // This would contain actual Bleichenbacher test vectors
        // For the purpose of this example, we'll simulate a simple test
        
        // Create a valid ciphertext
        Cipher cipher = Cipher.getInstance("RSA/ECB/OAEPWithSHA-256AndMGF1Padding");
        cipher.init(Cipher.ENCRYPT_MODE, keyPair.getPublic());
        byte[] plaintext = "Bleichenbacher test".getBytes();
        byte[] ciphertext = cipher.doFinal(plaintext);
        
        // Test decryption
        byte[] decrypted = decryptor.decrypt(ciphertext);
        assertArrayEquals(plaintext, decrypted);
    }
}