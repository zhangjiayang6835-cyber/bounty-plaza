# Fix for Issue #1898: Harden scripts/testnet-smoke.mjs with retries, exit codes, and a step summary

## Problem
`scripts/testnet-smoke.mjs` is the primary integration validation script run against live Circle Iris and smart contracts on testnet and mainnet. Public testnets and faucets frequently experience transient network lag, RPC 5xx errors, rate limits (HTTP 429), or temporary attestation delays. Without per-step retry, transient hiccups resulted in false positive failures. Furthermore, partial failures lacked structured duration/attempt summaries, post-burn failures risked double-spends if rerun blindly, and exit codes did not reliably reflect step-level failures.

## Solution
1. **Named Step Pipeline with Fast-Fail & Transient Retries**:
   - Decomposed each transfer case into four distinct steps: `fund/check`, `approve+burn`, `attestation wait`, and `mint`.
   - Built `isDeterministicError` to immediately fast-fail on invalid addresses, recipient readiness issues, or insufficient balance without retrying.
   - Built `isTransientError` to retry temporary network failures, HTTP 429/5xx, RPC outages, `txBadSeq`, and `AttestationNotReadyError` with configurable exponential backoff (`SMOKE_MAX_ATTEMPTS`, `SMOKE_BASE_DELAY_MS`).
2. **Post-Burn Recovery Protection**:
   - If a failure occurs post-burn, `error.burnTxHash` is captured and preserved.
   - Outputs ready-to-run `completeMint()` invocation instructions to complete the transfer manually without double-burning funds.
3. **Structured Step Summary & Non-Zero Exit Code**:
   - Collects per-step metrics (status, durationMs, attempt count, and details).
   - Prints a formatted tabular summary at the conclusion of test execution.
   - Tracks `failures` counter and exits with `process.exit(1)` if any step or case ultimately fails.
4. **Hermetic Test Suite**:
   - Verified in `tests/smoke-hardening.test.ts` and syntax-validated with `node --check`.

**Payout Wallet Address**: `0xC345C07229307d4f1c7935aD2cAe48e390215808`
