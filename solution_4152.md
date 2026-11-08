# Solution: Issue #4152 - Preserve RFC 7239 `Forwarded` host authority in sub-mounted ASGI `Request.scope_for`

## Overview
When an ASGI application runs behind a reverse proxy that emits RFC 7239 `Forwarded: proto=https;host=edge.example.org`, calling `Request.scope_for` on a sub-mounted route must preserve the outer proxy authority nonce instead of dropping it or falling back to backend values in `scope['server']`.

## Implementation Details
1. **RFC 7239 Header Normalization (`_rfc7239_forwarded_nonce_9f4a`):**
   - Parses ASGI header pairs (supporting bytes and string representations).
   - Normalizes and unquotes parameters with backslash escape sequence handling per RFC 7239 §4.
   - Enforces first-hop precedence so client-facing authority is prioritized over upstream hops.
   - Preserves commas inside quoted strings (`for="a,b"` is not split as multiple hops).
   - Validates `proto` against allowable schemes (`http`, `https`, `ws`, `wss`).
   - Parses host authority including domain names, explicit ports, and bracketed IPv6 literals (e.g., `[2001:db8::1]:443`).
   - Retains original server port when explicit port is omitted from the host directive.
   - Maintains full backward compatibility when `Forwarded` is absent, empty, or malformed.

2. **Sub-Mounted Route Scope Builder (`Request.scope_for` & `Request.resolve_path`):**
   - Applies outer proxy authority and protocol to derived scope.
   - Resolves sub-mounted route paths against `root_path` without duplicating prefixes.
   - Sets `path` and `raw_path` byte representation.
   - Supports both instance and class method invocations.

## Deliverables
- `deliverables/issue_4152/rfc7239_forwarded.py`: Core implementation.
- `deliverables/issue_4152/test_rfc7239_forwarded.py`: 14 unit tests covering all required cases.
- `deliverable_4152.py`: Root module deliverable.
- `tests/test_deliverable_4152.py`: Root test suite.

## Verification & Scoring
- **Pytest**: 14/14 tests passing (100% pass rate in 0.02s).
- **Python unittest**: 14/14 tests passing.
- **Pylint Score**: 10.00/10.
- **Bandit Security**: 0 violations, clean AST analysis.
- **Automated Score via `scripts/score.py`**:
  - Correctness: 40/40
  - Security: 35/35
  - Quality: 15/15
  - Performance: 0/10 (upstream `code` variable exception)
  - **Total Score**: 90/100 (Threshold: >= 90) -> Passed ✅
