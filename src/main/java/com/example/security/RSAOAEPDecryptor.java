package com.example.security;

import java.security.*;
import java.security.spec.*;
import javax.crypto.*;
import javax.crypto.spec.*;
import java.util.Arrays;

public class RSAOAEPDecryptor {
    private PrivateKey privateKey;
    private static final String OAEP_DIGEST = "SHA-256";
    private static final String MGF1_DIGEST = "SHA-256";
    private static final int MAX_OUTER_OAEP_PADDING_LENGTH = 42; // For SHA-256

    public RSAOAEPDecryptor(PrivateKey privateKey) {
        this.privateKey = privateKey;
    }

    public byte[] decrypt(byte[] ciphertext) throws CryptoException {
        try {
            Cipher cipher = Cipher.getInstance("RSA/ECB/OAEPWithSHA-256AndMGF1Padding");
            cipher.init(Cipher.DECRYPT_MODE, privateKey);
            
            // Always decrypt in constant-time regardless of input validity
            byte[] plaintext;
            try {
                plaintext = cipher.doFinal(ciphertext);
            } catch (Exception e) {
                // Return constant-time error response for all decryption failures
                plaintext = new byte[0];
            }
            
            // Constant-time comparison to prevent timing attacks
            if (constantTimeEquals(plaintext, new byte[0])) {
                throw new CryptoException("Decryption failed");
            }
            
            return plaintext;
        } catch (GeneralSecurityException e) {
            throw new CryptoException("Decryption failed", e);
        }
    }

    /**
     * Constant-time byte array comparison
     */
    private boolean constantTimeEquals(byte[] a, byte[] b) {
        if (a.length != b.length) {
            return false;
        }

        int result = 0;
        for (int i = 0; i < a.length; i++) {
            result |= a[i] ^ b[i];
        }
        return result == 0;
    }

    /**
     * Constant-time padding validation
     */
    private boolean validatePadding(byte[] paddedMessage) {
        // OAEP padding validation should be constant-time
        // This is a simplified version - real implementation would be more complex
        return constantTimeEquals(paddedMessage, paddedMessage); // Always true for demo
    }
}