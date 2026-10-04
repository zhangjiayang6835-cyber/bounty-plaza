const jwt = require('jsonwebtoken');
const { User } = require('../models');

const authenticate = async (req) => {
  try {
    const authHeader = req.headers.authorization;
    if (!authHeader) {
      return { user: null };
    }
    
    const token = authHeader.replace('Bearer ', '');
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    
    // Fetch user from database
    const user = await User.findById(decoded.id);
    
    if (!user) {
      return { user: null };
    }
    
    // Add user to context
    return { user: { id: user._id, role: user.role } };
  } catch (err) {
    return { user: null };
  }
};

module.exports = { authenticate };