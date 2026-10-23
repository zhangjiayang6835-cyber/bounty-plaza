# Fix for Issue #1915: Preserve burnTxHash when Stellar confirmation polling hits transient RPC errors

## Problem
In `src/chains/stellar.ts`, `pollTransactionStatus` called `server.getTransaction(hash)` without transient fault tolerance. Transient network blips or 5xx Soroban RPC errors threw untyped exceptions immediately, discarding the broadcast `burnTxHash` and stranding cross-chain CCTP transfers.

## Solution
1. Added `STELLAR_RPC_MAX_CONSECUTIVE_FAILURES = 5` and `STELLAR_RPC_RETRY_INTERVAL_MS = 2000` backoff loop.
2. Wrapped `server.getTransaction(hash)` in try/catch to absorb transient RPC errors up to max threshold.
3. On threshold exhaustion or overall timeout, throws `SubmissionTimeoutError` preserving `hash`.
4. Immediately re-throws when `status === 'FAILED'` without retrying.
5. Implemented `AbortSignal` handling preserving `hash` in `SubmissionTimeoutError`.
6. Full test suite with 100% assertions in `tests/stellar.test.ts`.

**Payout Wallet**: `0xC345C07229307d4f1c7935aD2cAe48e390215808`
