<content>
const winston = require('winston');

// Create logs directory if it doesn't exist
const logDir = './logs';
if (!require('fs').existsSync(logDir)) {
  require('fs').mkdirSync(logDir);
}

// Custom format to exclude sensitive data
const sensitiveDataFilter = winston.format((info, opts) => {
  if (info.message) {
    // Redact sensitive fields from message
    const sensitiveFields = ['secret', 'token', 'password', 'otpauth'];
    let message = info.message;
    
    sensitiveFields.forEach(field => {
      const regex = new RegExp(`${field}=([^&]*)`, 'gi');
      message = message.replace(regex, `${field}=[REDACTED]`);
    });
    
    // Redact QR codes which contain secrets
    const qrRegex = /(data:image\/png;base64,[A-Za-z0-9+/=]+)/g;
    message = message.replace(qrRegex, 'QR_CODE=[REDACTED]');
    
    info.message = message;
  }
  
  return info;
});

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json(),
    sensitiveDataFilter()
  ),
  defaultMeta: { service: 'bounty-plaza' },
  transports: [
    new winston.transports.File({ filename: 'logs/error.log', level: 'error' }),
    new winston.transports.File({ filename: 'logs/combined.log' }),
  ],
});

if (process.env.NODE_ENV !== 'production') {
  logger.add(new winston.transports.Console({
    format: winston.format.simple()
  }));
}

module.exports = logger;