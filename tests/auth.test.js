<content>
const jwt = require('../src/auth/jwt');
const jwtLib = require('jsonwebtoken');
const fs = require('fs');
const path = require('path');

// Test data
const testKey = jwt.ALLOWED_KEYS.key1;
const testPayload = { userId: 123, username: 'testuser' };

describe('JWT Authentication', () => {
  describe('verifyToken', () => {
    it('should verify a valid token', () => {
      const token = jwtLib.sign(testPayload, testKey, { algorithm: 'RS256', kid: 'key1' });
      const decoded = jwt.verifyToken(token);
      expect(decoded.userId).toBe(testPayload.userId);
      expect(decoded.username).toBe(testPayload.username);
    });

    it('should reject token with invalid kid', () => {
      const privateKey = fs.readFileSync(path.join(__dirname, '../src/keys/key1_private.pem'));
      const token = jwtLib.sign(testPayload, privateKey, { algorithm: 'RS256', kid: 'invalid_kid' });
      expect(() => jwt.verifyToken(token)).toThrow('Invalid kid: not in allowed list');
    });

    it('should reject token with path traversal in kid', () => {
      const privateKey = fs.readFileSync(path.join(__dirname, '../src/keys/key1_private.pem'));
      const token = jwtLib.sign(testPayload, privateKey, { algorithm: 'RS256', kid: '../../etc/passwd' });
      expect(() => jwt.verifyToken(token)).toThrow('Invalid kid: not in allowed list');
    });

    it('should reject token with null bytes in kid', () => {
      const privateKey = fs.readFileSync(path.join(__dirname, '../src/keys/key1_private.pem'));
      const token = jwtLib.sign(testPayload, privateKey, { algorithm: 'RS256', kid: 'key1\x00../etc/passwd' });
      expect(() => jwt.verifyToken(token)).toThrow('Invalid kid: not in allowed list');
    });

    it('should reject malformed token', () => {
      expect(() => jwt.verifyToken('not.a.jwt.token')).toThrow('Invalid token: missing or malformed kid');
    });

    it('should reject token without kid', () => {
      const token = jwtLib.sign(testPayload, testKey, { algorithm: 'RS256' });
      expect(() => jwt.verifyToken(token)).toThrow('Invalid token: missing or malformed kid');
    });
  });

  describe('getPublicKey', () => {
    it('should return public key for valid kid', () => {
      const publicKey = jwt.getPublicKey('key1');
      expect(publicKey).toBeTruthy();
      expect(typeof publicKey).toBe('string');
    });

    it('should throw error for invalid kid', () => {
      expect(() => jwt.getPublicKey('invalid_kid')).toThrow('Invalid kid: not in allowed list');
    });
  });
});