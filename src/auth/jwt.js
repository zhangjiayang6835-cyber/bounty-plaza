const fs = require('fs');
const path = require('path');
const jwt = require('jsonwebtoken');

// Predefined whitelist of valid key IDs
const VALID_KIDS = ['key1', 'key2', 'service-a', 'service-b'];

function getPublicKeyPath(kid) {
    // Validate kid against whitelist
    if (!VALID_KIDS.includes(kid)) {
        throw new Error('Invalid Key ID (kid)');
    }
    
    // Construct path using only the validated kid
    return path.join(__dirname, '..', '..', 'keys', kid + '.pub');
}

function verifyToken(token) {
    try {
        // Decode token without verification first to get the kid
        const decoded = jwt.decode(token, { complete: true });
        
        if (!decoded || !decoded.header || !decoded.header.kid) {
            throw new Error('Token missing or invalid kid in header');
        }
        
        const kid = decoded.header.kid;
        
        // Get the public key path
        const publicKeyPath = getPublicKeyPath(kid);
        
        // Read the public key
        const publicKey = fs.readFileSync(publicKeyPath);
        
        // Verify the token with the public key
        return jwt.verify(token, publicKey);
    } catch (error) {
        throw new Error('Token verification failed: ' + error.message);
    }
}

module.exports = {
    verifyToken,
    getPublicKeyPath
};