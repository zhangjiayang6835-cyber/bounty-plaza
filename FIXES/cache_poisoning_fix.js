function sanitizeCacheKeyHeaders(req, res, next) {
  // Strip unkeyed untrusted forwarding headers to prevent Web Cache Poisoning (Issue #290)
  delete req.headers['x-forwarded-host'];
  delete req.headers['x-original-url'];
  delete req.headers['x-rewrite-url'];
  delete req.headers['x-host'];
  next();
}

module.exports = sanitizeCacheKeyHeaders;
