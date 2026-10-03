const User = require('../models/User');

// Login function with proper validation
exports.login = async (req, res) => {
  try {
    // Validate input types
    if (typeof req.body.username !== 'string' || typeof req.body.password !== 'string') {
      return res.status(400).json({ 
        success: false, 
        message: 'Invalid input types. Username and password must be strings.' 
      });
    }

    // Trim whitespace
    const username = req.body.username.trim();
    const password = req.body.password.trim();

    // Find user by username (exact match)
    const user = await User.findOne({ username });

    // Check if user exists and password is correct
    if (!user || !(await user.comparePassword(password))) {
      return res.status(401).json({ 
        success: false, 
        message: 'Invalid credentials' 
      });
    }

    // If authentication successful
    res.status(200).json({
      success: true,
      message: 'Authentication successful',
      user: {
        id: user._id,
        username: user.username,
        role: user.role
      }
    });
  } catch (error) {
    console.error('Authentication error:', error);
    res.status(500).json({ 
      success: false, 
      message: 'Internal server error' 
    });
  }
};

// Register function
exports.register = async (req, res) => {
  try {
    // Validate input types
    if (typeof req.body.username !== 'string' || typeof req.body.password !== 'string') {
      return res.status(400).json({ 
        success: false, 
        message: 'Invalid input types. Username and password must be strings.' 
      });
    }

    // Trim whitespace
    const username = req.body.username.trim();
    const password = req.body.password.trim();

    // Check if user already exists
    const existingUser = await User.findOne({ username });
    if (existingUser) {
      return res.status(409).json({ 
        success: false, 
        message: 'Username already exists' 
      });
    }

    // Create new user (password will be hashed automatically by the schema)
    const user = new User({
      username,
      password
    });

    await user.save();

    res.status(201).json({
      success: true,
      message: 'User registered successfully',
      user: {
        id: user._id,
        username: user.username,
        role: user.role
      }
    });
  } catch (error) {
    console.error('Registration error:', error);
    res.status(500).json({ 
      success: false, 
      message: 'Internal server error' 
    });
  }
};