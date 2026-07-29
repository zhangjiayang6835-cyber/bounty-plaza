const path = require('path');

function sanitizeJwtKid(kid, trustedKeysMap) {
  if (!kid || typeof kid !== 'string') {
    throw new Error('JWT Kid parameter is missing or invalid');
  }

  // Prevent Directory Traversal / Header Injection (Issue #286)
  const normalizedKid = path.basename(kid).replace(/[^a-zA-Z0-9_-]/g, '');
  if (!trustedKeysMap.has(normalizedKid)) {
    throw new Error('JWT Kid key not found in trusted key repository');
  }

  return trustedKeysMap.get(normalizedKid);
}

module.exports = sanitizeJwtKid;
