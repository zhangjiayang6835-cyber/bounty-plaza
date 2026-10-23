# Fix for Issue #1896: Export convertPrecision and add 6↔7 decimal round-trip tests

## Problem
In `src/utils/encoding.ts`, `convertPrecision` implements the core Arc (6 decimals) ↔ Stellar (7 decimals) bigint conversion, but was not exported from the public package entry point `src/index.ts`. Callers and integrators had to re-implement bigint decimal scaling themselves, and dedicated round-trip unit test coverage was absent.

## Solution
1. Re-exported `convertPrecision` from `src/index.ts`.
2. Added comprehensive unit tests in `tests/encoding.test.ts` verifying:
   - 6 -> 7 upscale exactness.
   - 7 -> 6 downscale truncation.
   - Identity when source and destination decimals match.
   - Zero-value inputs.
   - Round-trip conversions with documented expected values.

**Payout Wallet Address**: `0xC345C07229307d4f1c7935aD2cAe48e390215808`
