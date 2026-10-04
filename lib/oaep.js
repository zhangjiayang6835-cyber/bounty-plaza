const crypto = require('crypto');

// OAEP parameters
const HASH_ALGORITHM = 'sha256';
const LABEL = Buffer.alloc(0);
const MGF1_HASH = HASH_ALGORITHM;
const ENCODING_BUFFER_SIZE = 42; // For SHA-256: 1 (zero byte) + 32 (hash) + 8 (seed length) + 2 (length prefixes)

/**
 * Performs constant-time comparison of two buffers
 * @param {Buffer} a - First buffer
 * @param {Buffer} b - Second buffer
 * @returns {boolean} - True if buffers are equal, false otherwise
 */
function constantTimeEqual(a, b) {
    if (a.length !== b.length) {
        return false;
    }
    
    let result = 0;
    for (let i = 0; i < a.length; i++) {
        result |= a[i] ^ b[i];
    }
    
    return result === 0;
}

/**
 * Generates a mask generation function (MGF1)
 * @param {Buffer} mgfSeed - The seed for the mask generation
 * @param {number} maskLen - The length of the mask to generate
 * @returns {Buffer} - The generated mask
 */
function mgf1(mgfSeed, maskLen) {
    const hLen = crypto.createHash(MGF1_HASH).digestLength;
    const T = Buffer.alloc(maskLen);
    let counter = 0;
    
    for (let i = 0; i < maskLen; i += hLen) {
        const C = Buffer.alloc(4);
        C.writeUInt32BE(counter, 0);
        
        const hash = crypto.createHash(MGF1_HASH)
            .update(mgfSeed)
            .update(C)
            .digest();
            
        hash.copy(T, i);
        counter++;
    }
    
    return T.slice(0, maskLen);
}

/**
 * Decodes OAEP-padded data
 * @param {Buffer} encoded - The encoded data to decode
 * @param {number} keySize - The size of the RSA key in bytes
 * @param {Object} [options] - Optional parameters
 * @param {Buffer} [options.label] - The label for OAEP
 * @returns {Buffer} - The decoded plaintext
 * @throws {Error} - If decoding fails
 */
function decodeOAEP(encoded, keySize, options = {}) {
    const { label = LABEL } = options;
    const hLen = crypto.createHash(HASH_ALGORITHM).digestLength;
    
    // Check encoded length
    if (encoded.length !== keySize || encoded.length < 2 * hLen + 2) {
        throw new Error('Decryption error');
    }
    
    // Separate the maskedSeed and maskedDB
    const maskedSeed = encoded.slice(0, hLen);
    const maskedDB = encoded.slice(hLen);
    
    // Generate the seed mask
    const seedMask = mgf1(maskedDB, hLen);
    
    // Recover the seed
    const seed = Buffer.alloc(hLen);
    for (let i = 0; i < hLen; i++) {
        seed[i] = maskedSeed[i] ^ seedMask[i];
    }
    
    // Generate the dbMask
    const dbMask = mgf1(seed, keySize - hLen - 1);
    
    // Recover the db
    const db = Buffer.alloc(keySize - hLen - 1);
    for (let i = 0; i < db.length; i++) {
        db[i] = maskedDB[i] ^ dbMask[i];
    }
    
    // Extract the lHash and the message
    const lHash = crypto.createHash(HASH_ALGORITHM).update(label).digest();
    const dbHash = db.slice(0, hLen);
    
    // Check if the dbHash matches the lHash
    if (!constantTimeEqual(dbHash, lHash)) {
        throw new Error('Decryption error');
    }
    
    // Check the padding
    const padding = db.slice(hLen);
    let zeroPos = -1;
    
    for (let i = 0; i < padding.length; i++) {
        if (padding[i] === 0x00) {
            zeroPos = i;
            break;
        }
    }
    
    if (zeroPos === -1 || zeroPos === 0) {
        throw new Error('Decryption error');
    }
    
    // Check if all remaining bytes are zero
    for (let i = zeroPos + 1; i < padding.length; i++) {
        if (padding[i] !== 0x00) {
            throw new Error('Decryption error');
        }
    }
    
    // Return the message
    return padding.slice(zeroPos + 1);
}

/**
 * Encrypts data using RSA-OAEP
 * @param {Buffer} message - The message to encrypt
 * @param {Object} key - The RSA public key
 * @param {Object} [options] - Optional parameters
 * @param {Buffer} [options.label] - The label for OAEP
 * @returns {Buffer} - The encrypted ciphertext
 */
function encryptOAEP(message, key, options = {}) {
    const { label = LABEL } = options;
    const keySize = key.modulus.byteLength;
    const hLen = crypto.createHash(HASH_ALGORITHM).digestLength;
    
    // Check message length
    if (message.length > keySize - 2 * hLen - 2) {
        throw new Error('Message too long');
    }
    
    // Generate the label hash
    const lHash = crypto.createHash(HASH_ALGORITHM).update(label).digest();
    
    // Create the DB
    const db = Buffer.alloc(keySize - hLen - 1);
    lHash.copy(db);
    
    // Add padding
    db.writeUInt16BE(0x0001, hLen);
    message.copy(db, hLen + 1);
    
    // Generate random seed
    const seed = crypto.randomBytes(hLen);
    
    // Generate the dbMask
    const dbMask = mgf1(seed, keySize - hLen - 1);
    
    // Mask the DB
    const maskedDB = Buffer.alloc(keySize - hLen - 1);
    for (let i = 0; i < maskedDB.length; i++) {
        maskedDB[i] = db[i] ^ dbMask[i];
    }
    
    // Generate the seed mask
    const seedMask = mgf1(maskedDB, hLen);
    
    // Mask the seed
    const maskedSeed = Buffer.alloc(hLen);
    for (let i = 0; i < hLen; i++) {
        maskedSeed[i] = seed[i] ^ seedMask[i];
    }
    
    // Create the encoded message
    const encoded = Buffer.alloc(keySize);
    maskedSeed.copy(encoded);
    maskedDB.copy(encoded, hLen);
    
    return encoded;
}

module.exports = {
    decodeOAEP,
    encryptOAEP,
    constantTimeEqual
};