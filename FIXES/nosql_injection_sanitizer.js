function sanitizeNoSQLInput(obj) {
  if (typeof obj !== 'object' || obj === null) {
    return obj;
  }

  if (Array.isArray(obj)) {
    return obj.map(sanitizeNoSQLInput);
  }

  const sanitized = {};
  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      // Strip dangerous MongoDB query operators ($gt, $ne, $where, $regex)
      if (key.startsWith('$')) {
        continue;
      }
      sanitized[key] = sanitizeNoSQLInput(obj[key]);
    }
  }
  return sanitized;
}

module.exports = sanitizeNoSQLInput;
