<content>
const jwt = require('jsonwebtoken');
const fs = require('fs');
const path = require('path');

// Predefined key IDs with their corresponding public keys
const ALLOWED_KEYS = {
  'key1': fs.readFileSync(path.join(__dirname, '../keys/public_key1.pem')),
  'key2': fs.readFileSync(path.join(__dirname, '../keys/public_key2.pem')),
  'service-a': fs.readFileSync(path.join(__dirname, '../keys/service_a.pem')),
  'service-b': fs.readFileSync(path.join(__dirname, '../keys/service_b.pem'))
};

/**
 * Verify JWT token with proper kid validation
 * @param {string} token - JWT token to verify
 * @returns {object} - Decoded token payload
 */
function verifyToken(token) {
  // First decode the token without verification to get the header
  const decodedHeader = jwt.decode(token, { complete: true });
  
  if (!decodedHeader || !decodedHeader.header || !decodedHeader.header.kid) {
    throw new Error('Invalid token: missing or malformed kid');
  }
  
  const kid = decodedHeader.header.kid;
  
  // Validate kid against allowed keys
  if (!ALLOWED_KEYS.hasOwnProperty(kid)) {
    throw new Error('Invalid kid: not in allowed list');
  }
  
  // Verify the token with the corresponding public key
  const publicKey = ALLOWED_KEYS[kid];
  
  try {
    const decoded = jwt.verify(token, publicKey);
    return decoded;
  } catch (err) {
    throw new Error('Token verification failed: ' + err.message);
  }
}

/**
 * Get public key for a specific kid (for testing purposes)
 * @param {string} kid - Key ID
 * @returns {string} - PEM formatted public key
 */
function getPublicKey(kid) {
  if (!ALLOWED_KEYS.hasOwnProperty(kid)) {
    throw new Error('Invalid kid: not in allowed list');
  }
  return ALLOWED_KEYS[kid];
}

module.exports = {
  verifyToken,
  getPublicKey,
  ALLOWED_KEYS
};