<content>
const express = require('express');
const router = express.Router();
const crypto = require('crypto');
const axios = require('axios');
const User = require('../models/User');
const session = require('express-session');

// Generate a random state parameter for OAuth
const generateState = () => {
  return crypto.randomBytes(32).toString('hex');
};

// Generate a random code verifier for PKCE
const generateCodeVerifier = () => {
  return crypto.randomBytes(32).toString('hex');
};

// Generate code challenge from code verifier
const generateCodeChallenge = (verifier) => {
  return crypto.createHash('sha256').update(verifier).digest('base64url');
};

// GitHub OAuth configuration
const GITHUB_CLIENT_ID = process.env.GITHUB_CLIENT_ID;
const GITHUB_CLIENT_SECRET = process.env.GITHUB_CLIENT_SECRET;
const GITHUB_REDIRECT_URI = process.env.GITHUB_REDIRECT_URI || 'http://localhost:3000/auth/github/callback';

// Start GitHub OAuth flow
router.get('/github', (req, res) => {
  const state = generateState();
  const codeVerifier = generateCodeVerifier();
  const codeChallenge = generateCodeChallenge(codeVerifier);
  
  // Store state and code verifier in session
  req.session.oauthState = state;
  req.session.codeVerifier = codeVerifier;
  
  // GitHub OAuth URL with PKCE
  const githubAuthUrl = `https://github.com/login/oauth/authorize?client_id=${GITHUB_CLIENT_ID}&redirect_uri=${encodeURIComponent(GITHUB_REDIRECT_URI)}&state=${state}&scope=repo&code_challenge=${codeChallenge}&code_challenge_method=S256`;
  
  res.redirect(githubAuthUrl);
});

// GitHub OAuth callback
router.get('/github/callback', async (req, res) => {
  const { code, state } = req.query;
  
  // Check if state parameter matches the one in session
  if (!state || state !== req.session.oauthState) {
    return res.status(403).send('Invalid state parameter');
  }
  
  // Clear state from session
  req.session.oauthState = null;
  
  if (!code) {
    return res.status(400).send('Authorization code not found');
  }
  
  try {
    // Exchange authorization code for access token
    const tokenResponse = await axios.post('https://github.com/login/oauth/access_token', {
      client_id: GITHUB_CLIENT_ID,
      client_secret: GITHUB_CLIENT_SECRET,
      code: code,
      redirect_uri: GITHUB_REDIRECT_URI,
      code_verifier: req.session.codeVerifier
    }, {
      headers: {
        'Accept': 'application/json'
      }
    });
    
    const { access_token } = tokenResponse.data;
    
    // Get user info from GitHub
    const userResponse = await axios.get('https://api.github.com/user', {
      headers: {
        'Authorization': `token ${access_token}`
      }
    });
    
    const githubUserData = userResponse.data;
    
    // Find or create user in our database
    let user = await User.findOne({ githubId: githubUserData.id });
    
    if (!user) {
      // Create new user
      user = new User({
        githubId: githubUserData.id,
        username: githubUserData.login,
        email: githubUserData.email,
        avatar: githubUserData.avatar_url,
        accessToken: access_token
      });
    } else {
      // Update existing user's access token
      user.accessToken = access_token;
    }
    
    await user.save();
    
    // Create session for the user
    req.session.userId = user._id;
    req.session.isAuthenticated = true;
    
    // Redirect to dashboard or home page
    res.redirect('/dashboard');
    
  } catch (error) {
    console.error('OAuth callback error:', error);
    res.status(500).send('Authentication failed');
  }
});

// Logout route
router.get('/logout', (req, res) => {
  req.session.destroy(err => {
    if (err) {
      return res.status(500).send('Could not log out');
    }
    res.redirect('/');
  });
});

module.exports = router;