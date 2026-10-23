# Fix for Issue #1906: Reject amounts whose precision exceeds destination chain's USDC decimals

## Problem
In cross-chain transfers (e.g. Stellar 7 decimals -> Arc 6 decimals), amounts carrying more significant precision than the destination chain supports (such as `"1.1234567"`) were accepted on the source chain without warning. On-chain contracts would subsequently truncate excess precision, silently reducing the received value without prior notice to the user.

## Solution
1. Implemented `significantDecimals(amount)` to accurately count significant fractional digits, ignoring harmless trailing zeros (e.g., `"1.1230000"` has 3 significant decimals).
2. Implemented `assertDestinationPrecision(amount, destination)` in `src/utils/amount.ts`.
3. Integrated the check into the pre-flight phase of `transfer()` before any approval or burn transactions are broadcast.
4. Throws typed `AmountPrecisionError` carrying `amount`, `precision`, `supportedDecimals`, and `destination`.
5. Full hermetic unit tests in `tests/amount.test.ts`.

**Payout Wallet Address**: `0xC345C07229307d4f1c7935aD2cAe48e390215808`
