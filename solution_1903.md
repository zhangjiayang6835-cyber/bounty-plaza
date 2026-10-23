# Fix for Issue #1903: Unit tests for src/errors.ts and a public export surface snapshot

## Problem
`src/errors.ts` defines the SDK's entire failure taxonomy (`TransferError`, `AttestationNotReadyError`, `IrisRequestError`, `SubmissionTimeoutError`, `AmountPrecisionError`), but lacked dedicated unit testing. Constructor parameters, discriminator codes, `instanceof` prototypes, and public exports from `src/index.ts` were unverified against regression.

## Solution
1. Added `tests/errors.test.ts` verifying constructor wiring, property assignments, prototype chains, and discriminator codes for all error classes.
2. Added `tests/exports.test.ts` snapshot testing the exact sorted list of public runtime and type exports from `src/index.ts`.
3. Verified full test suite runs cleanly under Vitest without external additions.

**Payout Wallet Address**: `0xC345C07229307d4f1c7935aD2cAe48e390215808`
