function graphqlBatchLimiter(maxBatchSize = 5) {
  return function (req, res, next) {
    if (Array.isArray(req.body)) {
      if (req.body.length > maxBatchSize) {
        return res.status(400).json({
          error: `GraphQL batch query limit exceeded. Max allowed queries: ${maxBatchSize}`
        });
      }
    }
    next();
  };
}

module.exports = graphqlBatchLimiter;
