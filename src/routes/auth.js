<content>
const express = require('express');
const router = express.Router();
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const User = require('../models/User');
const { validateLoginInput, preventNoSqlInjection } = require('../middleware/auth');

// Login route
router.post('/login', validateLoginInput, preventNoSqlInjection, async (req, res) => {
  try {
    const { username, password } = req.body;
    
    // Find user by username (now safe from injection)
    const user = await User.findOne({ username });
    
    if (!user) {
      return res.status(400).json({ 
        success: false, 
        message: 'Invalid credentials' 
      });
    }
    
    // Check if password matches (bcrypt handles salt and hashing)
    const isMatch = await bcrypt.compare(password, user.password);
    
    if (!isMatch) {
      return res.status(400).json({ 
        success: false, 
        message: 'Invalid credentials' 
      });
    }
    
    // Create and sign JWT
    const payload = {
      user: {
        id: user.id
      }
    };
    
    jwt.sign(
      payload, 
      process.env.JWT_SECRET || 'your_jwt_secret', 
      { expiresIn: '1h' }, 
      (err, token) => {
        if (err) throw err;
        res.json({
          success: true,
          token
        });
      }
    );
    
  } catch (err) {
    console.error(err);
    res.status(500).json({ 
      success: false, 
      message: 'Server error' 
    });
  }
});

module.exports = router;
</content>