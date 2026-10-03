<content>
const { body, validationResult } = require('express-validator');

// Validate and sanitize login input
const validateLoginInput = [
  // Ensure username is a string
  body('username')
    .isString()
    .withMessage('Username must be a string')
    .trim()
    .escape(),
    
  // Ensure password is a string
  body('password')
    .isString()
    .withMessage('Password must be a string')
    .trim()
    .escape(),
    
  // Check for validation errors
  (req, res, next) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ 
        success: false, 
        message: 'Invalid input',
        errors: errors.array()
      });
    }
    next();
  }
];

// Middleware to prevent NoSQL injection
const preventNoSqlInjection = (req, res, next) => {
  // Check if username or password contains MongoDB operators
  const suspiciousPatterns = [
    /\$ne/, /\$gt/, /\$gte/, /\$lt/, /\$lte/, 
    /\$in/, /\$nin/, /\$exists/, /\$size/, /\$type/,
    /\$or/, /\$and/, /\$not/, /\$nor/, /\$regex/,
    /\$expr/, /\$jsonSchema/, /\$where/, /\$text/, /\$search/,
    /\$aggregate/, /\$group/, /\$project/, /\$sort/, /\$limit/, /\$skip/
  ];
  
  const { username, password } = req.body;
  
  // Check if any suspicious pattern is found
  const hasSuspiciousPattern = suspiciousPatterns.some(pattern => {
    return pattern.test(username) || pattern.test(password);
  });
  
  if (hasSuspiciousPattern) {
    return res.status(400).json({
      success: false,
      message: 'Invalid input detected'
    });
  }
  
  next();
};

module.exports = {
  validateLoginInput,
  preventNoSqlInjection
};
</content>