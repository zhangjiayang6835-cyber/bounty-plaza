const crypto = require('crypto');

function validateOAuthState(req, res, next) {
  const sessionState = req.session ? req.session.oauthState : null;
  const paramState = req.query.state;

  if (!sessionState || !paramState || !crypto.timingSafeEqual(Buffer.from(sessionState), Buffer.from(paramState))) {
    return res.status(403).json({ error: 'OAuth State CSRF Validation Failed (Issue #296)' });
  }
  next();
}

module.exports = validateOAuthState;
