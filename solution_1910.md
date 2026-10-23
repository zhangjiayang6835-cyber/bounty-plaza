# Fix for Issue #1910: Add structured progress callbacks to transfer()

## Problem
In `src/transfer.ts`, `transfer()` ran multiple stages (recipient check, approve, burn, attestation polling, mint) without stage-level progress emission. Callers, web applications, and backend services could not observe progress or measure stage durations.

## Solution
1. Defined `TransferProgressEvent` as a discriminated union covering:
   - `recipient-check`
   - `approve`
   - `burn-submitted`
   - `burn-confirmed`
   - `attestation`
   - `mint-submitted`
   - `mint-confirmed`
2. Added optional `options.onProgress?: (event: TransferProgressEvent) => void` to `TransferOptionsBase`.
3. Emitted events at exact stage boundaries carrying tx hashes and stage data.
4. Swallowed callback errors to ensure user progress handlers never crash or break the financial transfer flow.
5. Exported `TransferProgressEvent` and event subtypes from `src/index.ts`.
6. Full hermetic unit tests in `tests/progress.test.ts`.

**Payout Wallet Address**: `0xC345C07229307d4f1c7935aD2cAe48e390215808`
