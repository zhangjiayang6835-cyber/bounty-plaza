# Solution for Issue #4143: Preserve RFC 7239 `Forwarded` host authority in sub-mounted ASGI `Request.scope_for`

## Problem Description
When an ASGI application runs behind a reverse proxy emitting standard RFC 7239 headers (`Forwarded: proto=https;host=edge.example.org`), resolving sub-mounted routes via `Request.scope_for` inadvertently discards the outer proxy host authority and falls back to internal backend identifiers in `scope['server']`.

## Solution Architecture
1. **RFC 7239 Header Normalization (`_rfc7239_forwarded_nonce_9f4a`):**
   - Parses ASGI header pairs (supporting both `bytes` and `str` types).
   - Extracts directive `host=<authority>` with quotes unquoted and case-insensitive matching.
   - Extracts `proto=<scheme>` to maintain scheme synchronization.
2. **Sub-Mounted Route Scope Builder (`Request.scope_for`):**
   - Applies normalized host authority and scheme to the sub-scope `server` tuple and `host_authority` metadata.
   - Preserves full backward compatibility when the `Forwarded` header is absent by using existing `scope['server']` values.
   - Supports both instance invocations (`req.scope_for(...)`) and class invocations (`Request.scope_for(scope, ...)`).

## Deliverables
- `solutions/issue_4143/asgi_forwarded.py`: Complete implementation of RFC 7239 normalization functions, `Request`, `SubScope`, and `Router`.
- `solutions/issue_4143/test_asgi_forwarded.py`: 6 test cases testing authority preservation, port preservation, absence fallback, and router path integration.

## Upstream References
- Original Bounty: [WholeTroutMedia/oss-verification-sandbox#1](https://github.com/WholeTroutMedia/oss-verification-sandbox/issues/1)
- Upstream PR: [WholeTroutMedia/oss-verification-sandbox#8](https://github.com/WholeTroutMedia/oss-verification-sandbox/pull/8)
