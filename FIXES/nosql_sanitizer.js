function sanitizeNoSqlInput(obj) {
  if (obj instanceof Object) {
    for (const key in obj) {
      if (key.startsWith('$')) {
        delete obj[key]; // Strip dangerous MongoDB operators ($gt, $ne, $where)
      } else {
        sanitizeNoSqlInput(obj[key]);
      }
    }
  }
  return obj;
}

module.exports = function nosqlSanitizerMiddleware(req, res, next) {
  if (req.body) sanitizeNoSqlInput(req.body);
  if (req.query) sanitizeNoSqlInput(req.query);
  if (req.params) sanitizeNoSqlInput(req.params);
  next();
};
