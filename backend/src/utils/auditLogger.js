<content>
const fs = require('fs');
const path = require('path');

// Create audit log directory if it doesn't exist
const auditLogDir = path.join(__dirname, '../../logs/audit');
if (!fs.existsSync(auditLogDir)) {
  fs.mkdirSync(auditLogDir, { recursive: true });
}

// Get current date for log file name
const currentDate = new Date().toISOString().split('T')[0];
const auditLogFile = path.join(auditLogDir, `audit-${currentDate}.log`);

const auditLogger = {
  log(action, data) {
    const logEntry = {
      timestamp: new Date().toISOString(),
      action,
      data
    };
    
    // Write to audit log file
    fs.appendFileSync(auditLogFile, JSON.stringify(logEntry) + '\n');
    
    // Also log to console for development (but not in production)
    if (process.env.NODE_ENV !== 'production') {
      console.log('[AUDIT LOG]', logEntry);
    }
  }
};

module.exports = auditLogger;