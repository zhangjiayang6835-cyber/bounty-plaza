const jwt = require('jsonwebtoken');
const { User } = require('../models');

const authMiddleware = async (req) => {
  try {
    // Get token from header
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return { user: null };
    }

    // Extract token
    const token = authHeader.split(' ')[1];

    // Verify token
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    
    // Find user by ID
    const user = await User.findById(decoded.id).select('-password');
    
    // Return user context
    return { user };
  } catch (error) {
    // Return null user if authentication fails
    return { user: null };
  }
};

module.exports = { authMiddleware };