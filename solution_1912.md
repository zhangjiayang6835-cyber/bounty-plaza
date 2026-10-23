# Fix for Issue #1912: checkStellarRecipientReady must not report RPC outages as missing accounts

## Problem
In `src/chains/stellar.ts`, `checkStellarRecipientReady` previously wrapped `server.getAccount(recipient)` in a catch-all block returning `{ exists: false, hasTrustline: false, ready: false }`. Consequently, infrastructure failures (DNS drops, connection resets, HTTP 503, or rate limits on public RPCs) were falsely reported as "recipient does not exist yet", erroneously prompting users to fund an account that already exists.

## Solution
1. Introduced `isAccountNotFoundError(err)` helper to strictly differentiate account-not-found errors from transport/network failures.
2. Only mapped genuine account-not-found errors to `exists: false`.
3. Transport, HTTP 5xx, or RPC outages propagate as errors so callers can retry or handle infrastructure issues appropriately.
4. Preserved `AbortSignal` handling.
5. Unit tests covering both account-not-found and transport/5xx branches in `tests/stellar.test.ts`.

**Payout Wallet Address**: `0xC345C07229307d4f1c7935aD2cAe48e390215808`
