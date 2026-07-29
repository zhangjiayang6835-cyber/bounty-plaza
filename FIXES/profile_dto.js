function profileDtoMassAssignmentGuard(req, res, next) {
  const allowedFields = ['displayName', 'bio', 'avatarUrl', 'theme'];
  const sanitized = {};

  if (req.body) {
    for (const field of allowedFields) {
      if (req.body[field] !== undefined) {
        sanitized[field] = req.body[field];
      }
    }
    req.body = sanitized; // Block unauthorized field assignment (e.g. isAdmin, balance)
  }
  next();
}

module.exports = profileDtoMassAssignmentGuard;
