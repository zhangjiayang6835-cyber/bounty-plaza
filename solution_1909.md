# Fix for Issue #1909: Make estimateFee agree with transfer() on maxFee and maxWait fallback

## Problem
In `src/transfer.ts`, fast transfers were downgraded to standard when quoted fees exceeded `options.maxFee` or when duration exceeded `options.maxWait`. However, `estimateFee` in `src/estimate.ts` was unaware of these options, continually quoting fast mode and full fees. This caused decoratively quoted fees that did not match the actual transfer execution mode.

## Solution
1. Extracted `resolveFastFallback` pure decision helper shared by both `estimateFee()` and `transfer()`.
2. Extended `EstimateFeeParams` with optional `maxFee` and `maxWait` parameters.
3. If `maxWait` is lower than `FAST_DURATION_SECONDS` (15s), `estimateFee` immediately falls back to standard mode (duration 20s, fee "0") without querying the Iris API.
4. If the quoted fee exceeds `maxFee`, `estimateFee` falls back to standard mode (fee "0").
5. Added full unit tests in `tests/estimate.test.ts`.

**Payout Wallet Address**: `0xC345C07229307d4f1c7935aD2cAe48e390215808`
