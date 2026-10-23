# Fix for Issue #1914: Stop silently pricing Fast Transfers at zero when Iris returns no fast tier

## Problem
In `src/iris/poll.ts:fetchFastTransferFeeBps`, the code performed:
```ts
body.find((entry) => entry.finalityThreshold <= 1000);
return fastEntry?.minimumFee ?? 0;
```
If Iris returned an unexpected response shape, an empty array, or tiers with different thresholds, fast transfers were silently quoted as 0 fee. In `transfer()` and `estimateFee()`, this quoted the transfer as free. Additionally, non-OK HTTP responses threw a bare `Error` instead of the specialized `IrisRequestError` carrying status codes.

## Solution
1. Raised `IrisRequestError` carrying the HTTP status on non-OK responses.
2. Threw an informative error naming the source and destination domain pair when no entry has `finalityThreshold <= 1000`, preventing silent zero-fee quotation.
3. Successfully resolved `minimumFee` when the normal shape or exact 1000 threshold boundary is met.
4. Added 100% assertion unit test coverage in `tests/poll.test.ts` with mocked fetch scenarios.

**Payout Wallet Address**: `0xC345C07229307d4f1c7935aD2cAe48e390215808`
