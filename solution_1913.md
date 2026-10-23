# Fix for Issue #1913: Tolerate transient Iris failures in getAttestation and resolveBurn

## Problem
In `src/iris/poll.ts`, `pollForAttestation` tolerated up to 5 consecutive failures before failing, but `getAttestation` (used by `resolveBurn`) executed `pollOnce` only once without retry. Any momentary network hiccup or 5xx gateway error caused `resolveBurn` to fail immediately, falsely indicating the burn was unresolvable.

## Solution
1. Extracted `retryTransientFailures` helper utilizing the shared constant `IRIS_MAX_CONSECUTIVE_FAILURES = 5`.
2. Wrapped `getAttestation` with `retryTransientFailures` so that transient 5xx or connection dropouts are retried.
3. Preserved immediate return without retry on 404 / empty messages (raising `AttestationNotReadyError` as intended).
4. Full hermetic test coverage in `tests/poll.test.ts`.

**Payout Wallet Address**: `0xC345C07229307d4f1c7935aD2cAe48e390215808`
