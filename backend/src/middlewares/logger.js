<content>
const logger = require('../utils/logger');

const sensitiveFields = ['secret', 'token', 'password', 'otpauth'];

const requestLogger = (req, res, next) => {
  const originalSend = res.send;
  
  res.send = function (body) {
    // Clone response to avoid modifying original
    const responseBody = typeof body === 'object' ? JSON.parse(JSON.stringify(body)) : body;
    
    // Filter out sensitive fields from response body
    if (responseBody && typeof responseBody === 'object') {
      filterSensitiveFields(responseBody);
    }
    
    // Log request without sensitive data
    const logData = {
      method: req.method,
      url: req.originalUrl,
      query: filterSensitiveFields({...req.query}),
      body: filterSensitiveFields({...req.body}),
      params: filterSensitiveFields({...req.params}),
      timestamp: new Date().toISOString()
    };
    
    // Special handling for TOTP QR code endpoint
    if (req.originalUrl.includes('/api/2fa/generate-qr')) {
      logger.info('TOTP QR code generated', {
        endpoint: req.originalUrl,
        userId: req.user ? req.user.id : 'unknown',
        timestamp: new Date().toISOString()
      });
    } else {
      logger.info('Request processed', logData);
    }
    
    // Call original send
    originalSend.call(this, body);
  };
  
  next();
};

function filterSensitiveFields(obj) {
  if (!obj || typeof obj !== 'object') return obj;
  
  for (const key in obj) {
    if (sensitiveFields.some(field => key.toLowerCase().includes(field))) {
      obj[key] = '[REDACTED]';
    } else if (typeof obj[key] === 'object') {
      filterSensitiveFields(obj[key]);
    }
  }
  
  return obj;
}

module.exports = requestLogger;