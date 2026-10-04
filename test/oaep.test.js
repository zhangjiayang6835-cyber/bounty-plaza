const assert = require('assert');
const crypto = require('crypto');
const { decodeOAEP, encryptOAEP } = require('../lib/oaep');

describe('RSA-OAEP Implementation', () => {
    const keySize = 256; // 2048 bits
    const hLen = 32; // SHA-256 digest length
    
    // Generate a test RSA key pair
    const { publicKey, privateKey } = crypto.generateKeyPairSync('rsa', {
        modulusLength: 2048,
        publicKeyEncoding: {
            type: 'spki',
            format: 'pem'
        },
        privateKeyEncoding: {
            type: 'pkcs8',
            format: 'pem'
        }
    });
    
    // Convert PEM to keys for Node.js crypto module
    const publicKeyObj = crypto.createPublicKey(publicKey);
    const privateKeyObj = crypto.createPrivateKey(privateKey);
    
    describe('decodeOAEP', () => {
        it('should decode a valid OAEP message', () => {
            const message = Buffer.from('Hello, world!', 'utf8');
            const encoded = encryptOAEP(message, publicKeyObj);
            
            // Encrypt using Node.js built-in RSA-OAEP for comparison
            const builtInEncoded = crypto.publicEncrypt(
                {
                    key: publicKey,
                    padding: crypto.constants.RSA_PKCS1_OAEP_PADDING,
                    oaepHash: 'sha256'
                },
                message
            );
            
            // Decode using our implementation
            const decoded = decodeOAEP(encoded, keySize);
            
            assert.strictEqual(decoded.toString('utf8'), message.toString('utf8'));
        });
        
        it('should throw error for invalid encoded length', () => {
            const invalidEncoded = Buffer.alloc(keySize - 1);
            
            assert.throws(() => {
                decodeOAEP(invalidEncoded, keySize);
            }, /Decryption error/);
        });
        
        it('should throw error for too short encoded data', () => {
            const invalidEncoded = Buffer.alloc(2 * hLen + 1);
            
            assert.throws(() => {
                decodeOAEP(invalidEncoded, keySize);
            }, /Decryption error/);
        });
        
        it('should throw error for invalid lHash', () => {
            // Create a valid encoded message
            const message = Buffer.from('Hello, world!', 'utf8');
            const encoded = encryptOAEP(message, publicKeyObj);
            
            // Modify the first byte of the maskedDB to corrupt the lHash
            encoded[hLen] ^= 0xff;
            
            assert.throws(() => {
                decodeOAEP(encoded, keySize);
            }, /Decryption error/);
        });
        
        it('should throw error for invalid padding', () => {
            // Create a valid encoded message
            const message = Buffer.from('Hello, world!', 'utf8');
            const encoded = encryptOAEP(message, publicKeyObj);
            
            // Modify the padding to make it invalid
            const paddingStart = hLen + hLen + 1; // Start of padding
            encoded[paddingStart + 1] ^= 0xff; // Change a padding byte
            
            assert.throws(() => {
                decodeOAEP(encoded, keySize);
            }, /Decryption error/);
        });
        
        it('should throw error for missing zero byte in padding', () => {
            // Create a valid encoded message
            const message = Buffer.from('Hello, world!', 'utf8');
            const encoded = encryptOAEP(message, publicKeyObj);
            
            // Modify the padding to remove the zero byte
            const paddingStart = hLen + hLen; // Start of padding
            encoded[paddingStart] = 0x01; // Change the first byte to non-zero
            
            assert.throws(() => {
                decodeOAEP(encoded, keySize);
            }, /Decryption error/);
        });
        
        it('should always return the same error message for all failure cases', () => {
            const testCases = [
                () => {
                    const invalidEncoded = Buffer.alloc(keySize - 1);
                    decodeOAEP(invalidEncoded, keySize);
                },
                () => {
                    const invalidEncoded = Buffer.alloc(2 * hLen + 1);
                    decodeOAEP(invalidEncoded, keySize);
                },
                () => {
                    const message = Buffer.from('Hello, world!', 'utf8');
                    const encoded = encryptOAEP(message, publicKeyObj);
                    encoded[hLen] ^= 0xff; // Corrupt lHash
                    decodeOAEP(encoded, keySize);
                },
                () => {
                    const message = Buffer.from('Hello, world!', 'utf8');
                    const encoded = encryptOAEP(message, publicKeyObj);
                    const paddingStart = hLen + hLen + 1;
                    encoded[paddingStart + 1] ^= 0xff; // Corrupt padding
                    decodeOAEP(encoded, keySize);
                }
            ];
            
            const errorMessages = testCases.map(testCase => {
                try {
                    testCase();
                    return 'No error';
                } catch (e) {
                    return e.message;
                }
            });
            
            // All error messages should be the same
            const firstMessage = errorMessages[0];
            assert.strictEqual(errorMessages.every(msg => msg === firstMessage), true);
        });
        
        it('should pass Bleichenbacher test vectors', () => {
            // This test verifies that our implementation correctly handles
            // the Bleichenbacher attack scenarios
            
            // Generate a test message
            const message = Buffer.from('Test message', 'utf8');
            const encoded = encryptOAEP(message, publicKeyObj);
            
            // Test case 1: Valid ciphertext
            let decoded;
            assert.doesNotThrow(() => {
                decoded = decodeOAEP(encoded, keySize);
            });
            assert.strictEqual(decoded.toString('utf8'), message.toString('utf8'));
            
            // Test case 2: Ciphertext with modified first block
            const modifiedEncoded = Buffer.concat([
                encoded.slice(0, hLen),
                Buffer.from([0xff]), // Modify first byte of second block
                encoded.slice(hLen + 1)
            ]);
            
            assert.throws(() => {
                decodeOAEP(modifiedEncoded, keySize);
            }, /Decryption error/);
            
            // Test case 3: Ciphertext with modified second block
            const modifiedEncoded2 = Buffer.concat([
                encoded.slice(0, hLen + 1),
                Buffer.from([0xff]), // Modify first byte of second block
                encoded.slice(hLen + 2)
            ]);
            
            assert.throws(() => {
                decodeOAEP(modifiedEncoded2, keySize);
            }, /Decryption error/);
            
            // Test case 4: Ciphertext with all zeros
            const zeroEncoded = Buffer.alloc(keySize, 0x00);
            
            assert.throws(() => {
                decodeOAEP(zeroEncoded, keySize);
            }, /Decryption error/);
        });
    });
    
    describe('constantTimeEqual', () => {
        it('should return true for equal buffers', () => {
            const a = Buffer.from('test123', 'utf8');
            const b = Buffer.from('test123', 'utf8');
            
            assert.strictEqual(constantTimeEqual(a, b), true);
        });
        
        it('should return false for different buffers', () => {
            const a = Buffer.from('test123', 'utf8');
            const b = Buffer.from('test124', 'utf8');
            
            assert.strictEqual(constantTimeEqual(a, b), false);
        });
        
        it('should return false for buffers of different lengths', () => {
            const a = Buffer.from('test123', 'utf8');
            const b = Buffer.from('test12', 'utf8');
            
            assert.strictEqual(constantTimeEqual(a, b), false);
        });
    });
});