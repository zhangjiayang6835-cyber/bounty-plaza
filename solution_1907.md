# Fix for Issue #1907: Reject unsupported CCTP message versions in decodeCctpMessage

## Problem
In `src/utils/message.ts`, `decodeCctpMessage` verified only the minimum byte length before decoding fields at fixed V2 offsets. It never checked the header `version` or `burnBodyVersion`. If an unsupported wire version or non-burn payload was passed, fields were silently misdecoded (e.g., misreading amounts and recipients), which could lead to critical mint failures or fund routing errors.

## Solution
1. Added validation for `version === SUPPORTED_HEADER_VERSION` (1).
2. Added validation for `burnBodyVersion === SUPPORTED_BURN_BODY_VERSION` (1).
3. Throws explicit, descriptive errors identifying both the actual and expected versions.
4. Preserved existing V2 and forward-hook decoding logic.
5. Added unit test cases in `tests/message.test.ts` verifying version rejection.

**Payout Wallet Address**: `0xC345C07229307d4f1c7935aD2cAe48e390215808`
