# Fix for Issue #1904: Expose retry/backoff knobs for Stellar allowance wait and RPC-lag

## Problem
In `src/chains/stellar.ts`, two recovery loops had hard-coded compile-time constants with no caller control:
- `waitForAllowance` (lines 210–227): 6 attempts × 1500ms
- `retryOnTransientRpcLag` (lines 278–294): 3 attempts × 2000ms

## Solution
1. Defined and exported `StellarRetryOptions` (`{ attempts?: number; delayMs?: number }`) and exposed both `stellarRetry?: StellarRetryOptions` and flat `stellarRetryAttempts?: number` / `stellarRetryDelayMs?: number` on `TransferOptionsBase`, `burnUsdcOnStellar`, and `approveUsdcOnStellar`.
2. Threaded retry options through both `waitForAllowance` and `retryOnTransientRpcLag` while strictly preserving default values (`6 × 1500ms` and `3 × 2000ms`) when omitted.
3. Added input validation rejecting non-positive integers or booleans/floats.
4. Added comprehensive mocked-timer unit tests in `tests/stellar.test.ts` and `tests/test_stellar_retry_backoff.py`.
