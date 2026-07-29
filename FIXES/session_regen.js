function regenerateSessionOnLogin(req, res, next) {
  if (!req.session) return next();

  const oldData = { ...req.session };
  req.session.regenerate((err) => {
    if (err) return next(err);
    Object.assign(req.session, oldData);
    req.session.authenticatedAt = new Date().toISOString();
    next();
  });
}

module.exports = regenerateSessionOnLogin;
