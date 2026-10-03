<content>
const express = require('express');
const router = express.Router();
const crypto = require('crypto');
const { OAuth2Client } = require('google-auth-library');
const User = require('../models/User');
const session = require('express-session');

// Initialize OAuth2 client with Google
const oauth2Client = new OAuth2Client(
  process.env.GOOGLE_CLIENT_ID,
  process.env.GOOGLE_CLIENT_SECRET,
  `${process.env.BASE_URL}/auth/google/callback`
);

// Generate a secure random state parameter
function generateState() {
  return crypto.randomBytes(32).toString('hex');
}

// Generate a code verifier for PKCE
function generateCodeVerifier() {
  return crypto.randomBytes(32).toString('base64url');
}

// Generate code challenge from code verifier
function generateCodeChallenge(verifier) {
  return crypto
    .createHash('sha256')
    .update(verifier)
    .digest('base64url');
}

// @route   GET /auth/google
// @desc    Initiate Google OAuth2 flow with PKCE
router.get('/google', (req, res) => {
  // Generate state and code verifier
  const state = generateState();
  const codeVerifier = generateCodeVerifier();
  const codeChallenge = generateCodeChallenge(codeVerifier);
  
  // Store state and code verifier in session
  req.session.oauthState = state;
  req.session.codeVerifier = codeVerifier;
  
  // Generate authorization URL with PKCE parameters
  const authUrl = oauth2Client.generateAuthUrl({
    access_type: 'offline',
    prompt: 'consent',
    scope: ['profile', 'email'],
    state: state,
    code_challenge: codeChallenge,
    code_challenge_method: 'S256'
  });
  
  res.redirect(authUrl);
});

// @route   GET /auth/google/callback
// @desc    Handle Google OAuth2 callback with state validation
router.get('/google/callback', async (req, res) => {
  const { state, code } = req.query;
  
  // Verify state parameter matches session
  if (state !== req.session.oauthState) {
    return res.status(403).json({ error: 'Invalid state parameter' });
  }
  
  try {
    // Get the code verifier from session
    const codeVerifier = req.session.codeVerifier;
    
    // Get access token with PKCE
    const { tokens } = await oauth2Client.getToken({
      code: code,
      codeVerifier: codeVerifier
    });
    
    // Verify the ID token
    const ticket = await oauth2Client.verifyIdToken({
      idToken: tokens.id_token,
      audience: process.env.GOOGLE_CLIENT_ID
    });
    
    const payload = ticket.getPayload();
    const { sub, name, email, picture } = payload;
    
    // Find or create user
    let user = await User.findOne({ googleId: sub });
    if (!user) {
      user = new User({
        googleId: sub,
        name,
        email,
        picture
      });
      await user.save();
    }
    
    // Destroy the session state and code verifier
    req.session.oauthState = null;
    req.session.codeVerifier = null;
    
    // Set user session
    req.session.userId = user._id;
    
    res.redirect('/dashboard');
  } catch (error) {
    console.error('OAuth callback error:', error);
    res.status(500).json({ error: 'Authentication failed' });
  }
});

// @route   GET /auth/logout
// @desc    Logout user and clear session
router.get('/logout', (req, res) => {
  req.session.destroy(err => {
    if (err) {
      return res.status(500).json({ error: 'Logout failed' });
    }
    res.clearCookie('connect.sid');
    res.redirect('/');
  });
});

module.exports = router;