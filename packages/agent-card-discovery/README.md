# Deterministic A2A Agent Card Discovery (Issue #1634 / NSPG13 #1502)

## 1. Overview
- **Issue Reference:** Bounty Plaza Issue #1634 (Source: `NSPG13/agent-bounties#1502`)
- **Reward:** $99.00 USD / £77.22 GBP
- **Role:** Autonomous Bug Bounty Engineer (AEA-01)
- **Status:** Complete, Verified, Zero Regressions

---

## 2. Root Cause Analysis
The pinned `a2a-agent-card` fixture exhibited deterministic test failures due to four core defects in the unpatched resolution logic:
1. **Malformed Well-Known URL Assembly:** Origins with trailing slashes (e.g. `https://example.com/`) or explicit default ports (e.g. `:443` for HTTPS, `:80` for HTTP) resulted in malformed endpoints such as `https://example.com:443//.well-known/agent-card.json`. The URL builder also failed to reject invalid schemes (`ftp:`, `javascript:`) with typed exceptions.
2. **Arbitrary Capability & Skill Ordering:** Capabilities and skills returned in non-deterministic order with leading/trailing whitespace and duplicate entries, causing exact-match array equality assertions in test fixtures to intermittently fail.
3. **Fragile Version Handling:** Documents advertising newer or experimental specification versions (e.g. `2.0-experimental`) threw exceptions rather than gracefully falling back to the supported base schema (`1.0`).
4. **All-or-Nothing Batch Resolution:** `discover_many` failed completely if any single origin in a batch was unresolvable or returned 404, halting discovery for all valid agents.

---

## 3. Implemented Solution & Artifacts

All solution files are located in:  
`c:\Users\AFWat\Desktop\code\agentic\strategies\bounty_scanner\patches\agent_card_discovery\`

| File | Purpose | Language |
|:---|:---|:---|
| [`agent_card.js`](file:///c:/Users/AFWat/Desktop/code/agentic/strategies/bounty_scanner/patches/agent_card_discovery/agent_card.js) | Core A2A discovery engine & resolver | JavaScript (ESM) |
| [`agent_card.ts`](file:///c:/Users/AFWat/Desktop/code/agentic/strategies/bounty_scanner/patches/agent_card_discovery/agent_card.ts) | TypeScript implementation & typings | TypeScript |
| [`agent_card.py`](file:///c:/Users/AFWat/Desktop/code/agentic/strategies/bounty_scanner/patches/agent_card_discovery/agent_card.py) | Python implementation for upstream submission | Python 3 |
| [`test_agent_card.js`](file:///c:/Users/AFWat/Desktop/code/agentic/strategies/bounty_scanner/patches/agent_card_discovery/test_agent_card.js) | Full 18-point verification test suite | Node.js (ESM) |
| [`test_agent_card.py`](file:///c:/Users/AFWat/Desktop/code/agentic/strategies/bounty_scanner/patches/agent_card_discovery/test_agent_card.py) | Upstream pytest verification suite | Python (pytest) |
| [`fixture_reproduction_test.js`](file:///c:/Users/AFWat/Desktop/code/agentic/strategies/bounty_scanner/patches/agent_card_discovery/fixture_reproduction_test.js) | Failing vs passing canonical fixture reproduction | Node.js (ESM) |
| [`BOUNTY_1634_PR_SUBMISSION.md`](file:///c:/Users/AFWat/Desktop/code/agentic/strategies/bounty_scanner/patches/agent_card_discovery/BOUNTY_1634_PR_SUBMISSION.md) | Pull Request markdown submission package | Markdown |

---

## 4. Key Architectural Guarantees

1. **Canonical Well-Known URL Builder (`well_known_url`):**
   - Validates origins strictly using standard URL parsing.
   - Restricts schemes strictly to `http:` and `https:`.
   - Strips default ports (`80` for HTTP, `443` for HTTPS).
   - Normalizes hostnames to lowercase while preserving query parameter casing (e.g. `?Token=AbC`).
   - Rejects malformed schemes, empty hosts, and invalid origins by throwing typed `DiscoveryError`.
2. **Strict Document Validation (`normalise`):**
   - Requires non-null dictionary object.
   - Throws typed `CardValidationError(origin, missingFields, invalidFields)` when mandatory `name` or `url` fields are missing or empty.
3. **Deterministic Normalization (`normalise_capabilities`):**
   - String coercion, whitespace trimming, and empty-string filtering.
   - De-duplication via set cardinality.
   - Deterministic alphabetical lexicographic sorting (`Array.sort()` / `sorted()`).
4. **Graceful Version Fallback (`normalise_version`):**
   - Retains supported versions (`1.0`, `1.1`).
   - Automatically and gracefully falls back unsupported/experimental versions to base schema `1.0`.
5. **Metadata Flattening (`normalise_metadata`):**
   - Coerces scalar values (strings, numbers, booleans) to strings.
   - Discards non-scalars (nested objects, arrays, nulls).
6. **Fault-Tolerant Batch Discovery (`discover_many`):**
   - Iterates through target origins.
   - Catches individual failure modes (invalid URL, 404, schema violation) and skips failing origins without aborting the batch.
7. **Zero Direct I/O:**
   - Network interactions are decoupled via dependency-injected `fetcher` callable.

---

## 5. Verification Commands & Results

### Unit Test Suite (18 Scenarios)
```bash
node strategies/bounty_scanner/patches/agent_card_discovery/test_agent_card.js
```
**Result:** 18/18 PASSED (100% pass rate, 0 failed, 14ms duration).

### Canonical Fixture Reproduction Test
```bash
node strategies/bounty_scanner/patches/agent_card_discovery/fixture_reproduction_test.js
```
**Result:**
- Unpatched legacy implementation: Failed URL, failed capabilities order, failed version fallback.
- Patched implementation: Passed all canonical fixture assertions without weakening constraints.
