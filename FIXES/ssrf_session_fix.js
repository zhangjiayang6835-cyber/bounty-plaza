const url = require('url');

function isAllowedUrl(targetUrl) {
  const parsed = url.parse(targetUrl);
  const allowedHosts = ['api.myzubster.com', 'services.internal.net'];
  return allowedHosts.includes(parsed.hostname);
}

function ssrfAndSessionProtectionMiddleware(req, res, next) {
  // Regenerate session ID on authentication state change (Session Fixation Prevention)
  if (req.session && req.session.isNew) {
    req.session.regenerate((err) => {
      if (err) return res.status(500).json({ error: 'Session regeneration failed' });
    });
  }

  // SSRF URL validation
  const target = req.query.url || req.body.url;
  if (target && !isAllowedUrl(target)) {
    return res.status(400).json({ error: 'Blocked potential SSRF request to internal IP' });
  }

  next();
}

module.exports = ssrfAndSessionProtectionMiddleware;
