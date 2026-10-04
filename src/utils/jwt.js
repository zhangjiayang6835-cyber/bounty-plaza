<content>
const fs = require('fs');
const path = require('path');

// Predefined list of valid key IDs
const VALID_KIDS = ['key1', 'key2', 'key3']; // Add your actual key IDs here

/**
 * Verify JWT token and return decoded payload
 * @param {string} token - JWT token to verify
 * @returns {object} - Decoded JWT payload
 * @throws {Error} - If token is invalid or verification fails
 */
function verifyJWT(token) {
    const jwt = require('jsonwebtoken');
    
    try {
        // First decode without verification to get the kid
        const decoded = jwt.decode(token, { complete: true });
        
        if (!decoded || !decoded.header || !decoded.header.kid) {
            throw new Error('Invalid JWT: missing kid in header');
        }
        
        const kid = decoded.header.kid;
        
        // Validate kid against whitelist
        if (!VALID_KIDS.includes(kid)) {
            throw new Error(`Invalid kid: ${kid}. Only predefined keys are allowed`);
        }
        
        // Construct safe path to key file
        const keyPath = path.join(__dirname, '..', 'keys', `${kid}.pem`);
        
        // Check if key file exists
        if (!fs.existsSync(keyPath)) {
            throw new Error(`Key file not found: ${keyPath}`);
        }
        
        // Read the key file
        const secretKey = fs.readFileSync(keyPath, 'utf8');
        
        // Verify the token with the key
        const verified = jwt.verify(token, secretKey);
        
        return verified;
    } catch (error) {
        throw new Error(`JWT verification failed: ${error.message}`);
    }
}

module.exports = {
    verifyJWT
};
</content>