# Fix for Issue #1897: Validate input to bytes32ToStellarAddress

## Problem
In `src/utils/encoding.ts`, `bytes32ToStellarAddress` previously called `Buffer.from(hex, "hex")` without input validation. Invalid inputs (missing 0x prefix, odd lengths, non-hex characters, incorrect lengths) were silently truncated or accepted by Buffer, producing corrupted but valid-looking `G...` addresses instead of throwing.

## Solution
1. Added validation requiring 0x-prefixed, even-length, 64-hex-character (32-byte) strings.
2. Verified with regular expressions that the payload contains only hexadecimal characters.
3. Explicitly documented contract (C...) address decoding behavior.
4. Added unit tests in `tests/encoding.test.ts` verifying all validation rejections and round-trip conversions.

**Payout Wallet Address**: `0xC345C07229307d4f1c7935aD2cAe48e390215808`
