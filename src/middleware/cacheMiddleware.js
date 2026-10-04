<content>
const { createHash } = require('crypto');

// Headers that should be included in cache key calculation
const KEYED_HEADERS = [
  'accept',
  'accept-encoding',
  'accept-language',
  'cookie',
  'x-forwarded-host',
  'x-forwarded-proto',
  'host'
];

// Headers that should be stripped from requests before forwarding to origin
const FORBIDDEN_HEADERS = [
  'x-forwarded-for',
  'x-real-ip',
  'via',
  'x-cache',
  'x-cache-lookup',
  'x-cache-status'
];

// Headers that should be normalized for cache key calculation
const NORMALIZED_HEADERS = {
  'accept-encoding': (value) => {
    // Normalize accept-encoding to prevent cache poisoning
    const encodings = value.toLowerCase().split(',').map(e => e.trim());
    const normalized = encodings.sort().join(', ');
    return normalized.includes('gzip') || normalized.includes('deflate') 
      ? 'gzip, deflate' 
      : normalized;
  },
  'user-agent': (value) => {
    // Normalize user-agent to prevent cache poisoning
    return value.toLowerCase().includes('mobile') ? 'mobile' : 'desktop';
  }
};

/**
 * Middleware to handle cache key generation and header sanitization
 */
function cacheKeyMiddleware(req, res, next) {
  // Generate cache key based on request headers
  const cacheKey = generateCacheKey(req);
  
  // Add cache key to request object for downstream use
  req.cacheKey = cacheKey;
  
  // Sanitize headers before forwarding to origin
  sanitizeHeaders(req);
  
  // Set appropriate Vary header
  setVaryHeader(res);
  
  next();
}

/**
 * Generate a cache key based on relevant request headers
 */
function generateCacheKey(req) {
  const keyParts = [];
  
  // Add method and path
  keyParts.push(`${req.method}:${req.originalUrl || req.url}`);
  
  // Add relevant headers
  for (const header of KEYED_HEADERS) {
    const value = req.headers[header];
    if (value) {
      let normalizedValue = value;
      
      // Apply header normalization if defined
      if (NORMALIZED_HEADERS[header]) {
        normalizedValue = NORMALIZED_HEADERS[header](value);
      }
      
      keyParts.push(`${header}:${normalizedValue}`);
    }
  }
  
  // Create hash of the key parts
  const keyString = keyParts.join('|');
  return createHash('sha256').update(keyString).digest('hex');
}

/**
 * Sanitize headers to prevent cache poisoning
 */
function sanitizeHeaders(req) {
  // Remove forbidden headers
  for (const header of FORBIDDEN_HEADERS) {
    delete req.headers[header];
  }
  
  // Ensure X-Forwarded-Host is properly set
  if (!req.headers['x-forwarded-host']) {
    req.headers['x-forwarded-host'] = req.headers.host || 'localhost';
  }
  
  // Clean up other potentially dangerous headers
  if (req.headers['x-forwarded-for']) {
    req.headers['x-forwarded-for'] = '127.0.0.1';
  }
}

/**
 * Set Vary header to include all headers used in cache key
 */
function setVaryHeader(res) {
  const varyHeader = res.getHeader('vary') || '';
  const existingVary = typeof varyHeader === 'string' ? varyHeader.split(',') : [];
  
  // Add all keyed headers to Vary if not already present
  for (const header of KEYED_HEADERS) {
    if (!existingVary.some(h => h.trim().toLowerCase() === header.toLowerCase())) {
      existingVary.push(header);
    }
  }
  
  // Set normalized Vary header
  res.setHeader('vary', existingVary.map(h => h.trim()).join(', '));
}

module.exports = {
  cacheKeyMiddleware,
  generateCacheKey,
  sanitizeHeaders,
  setVaryHeader
};
</content>