function normalizeTransferEncodingHeader(req, res, next) {
  // Reject conflicting Content-Length and Transfer-Encoding headers (Issue #294)
  const hasCL = req.headers['content-length'] !== undefined;
  const hasTE = req.headers['transfer-encoding'] !== undefined;

  if (hasCL && hasTE) {
    return res.status(400).json({ error: 'HTTP Smuggling Protection: Conflicting CL.TE headers rejected.' });
  }
  next();
}

module.exports = normalizeTransferEncodingHeader;
