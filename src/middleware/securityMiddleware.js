<content>
const cacheConfig = require('../config/cacheConfig');

/**
 * Security middleware to handle header sanitization and validation
 */
function securityMiddleware(req, res, next) {
  // Check for suspicious headers
  if (cacheConfig.security.blockSuspiciousHeaders) {
    checkSuspiciousHeaders(req);
  }
  
  // Validate header size
  checkHeaderSize(req);
  
  // Sanitize user-controlled headers
  sanitizeUserHeaders(req);
  
  next();
}

/**
 * Check for suspicious headers that might indicate cache poisoning
 */
function checkSuspiciousHeaders(req) {
  const suspiciousHeaders = cacheConfig.security.suspiciousHeaders;
  
  for (const header of suspiciousHeaders) {
    if (req.headers[header]) {
      console.warn(`Suspicious header detected: ${header}`);
      // You might want to log this or take more aggressive action
      delete req.headers[header];
    }
  }
}

/**
 * Check if headers exceed maximum allowed size
 */
function checkHeaderSize(req) {
  let totalSize = 0;
  
  for (const [key, value] of Object.entries(req.headers)) {
    totalSize += key.length + value.length + 4; // +4 for ": " and newline
  }
  
  if (totalSize > cacheConfig.security.maxHeaderSize) {
    console.warn('Header size exceeds limit');
    // You might want to reject the request or truncate headers
  }
}

/**
 * Sanitize user-controlled headers to prevent cache poisoning
 */
function sanitizeUserHeaders(req) {
  // Normalize X-Forwarded-Host
  if (req.headers['x-forwarded-host']) {
    // Only allow valid hostnames
    const hostPattern = /^[a-zA-Z0-9.-]+$/;
    if (!hostPattern.test(req.headers['x-forwarded-host'])) {
      req.headers['x-forwarded-host'] = req.headers.host || 'localhost';
    }
  }
  
  // Normalize X-Forwarded-For
  if (req.headers['x-forwarded-for']) {
    // Only allow valid IP addresses
    const ipPattern = /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/;
    if (!ipPattern.test(req.headers['x-forwarded-for'])) {
      req.headers['x-forwarded-for'] = '127.0.0.1';
    }
  }
  
  // Remove other potentially dangerous headers
  const dangerousHeaders = [
    'x-http-method-override',
    'x-method-override',
    'x-rewrite-url',
    'via',
    'x-cache-lookup',
    'x-cache-status'
  ];
  
  for (const header of dangerousHeaders) {
    delete req.headers[header];
  }
}

module.exports = {
  securityMiddleware
};
</content>