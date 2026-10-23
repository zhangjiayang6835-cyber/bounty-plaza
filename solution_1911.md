# Fix for Issue #1911: Add AbortSignal support across transfer, completeMint, and attestation polling

## Problem
In the cross-chain bridge SDK, operations lacked external cancellation via `AbortSignal`. Long-running polling loops (Iris attestation polling, Soroban RPC status checks, allowance waiting) ran with fixed timeouts. Aborting an in-flight operation either was impossible or risked dropping the broadcast `burnTxHash`, stranding funds.

## Solution
1. Threaded `signal?: AbortSignal` through `TransferOptionsBase`, `CompleteMintOptions`, `transfer()`, `completeMint()`, and `resolveBurn()`.
2. Implemented abortable sleep loops that respond promptly to abort events instead of waiting for full interval expiry.
3. Pre-burn abort throws a plain `AbortError`, ensuring no funds or burns are initiated.
4. Post-burn abort throws `TransferError` carrying `burnTxHash` and `code: "TRANSFER_ABORTED"`, preserving the full recovery pathway for `completeMint()`.
5. Propagated `signal` into all Iris and chain fetch calls.
6. Full test suite in `tests/abort-signal.test.ts`.

**Payout Wallet Address**: `0xC345C07229307d4f1c7935aD2cAe48e390215808`
