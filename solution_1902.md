# Fix for Issue #1902: Demo app: recovery flow for post-burn failures using TransferError

## Problem
In `demos/wallet-transfer-demo`, when a cross-chain transfer completed the source-chain burn but failed during attestation polling or destination-chain minting, the failure previously surfaced as a dead-end error banner. Users had no recovery path other than restarting from scratch, which would trigger a second burn and double-spend funds.

## Solution
1. **TransferError Detection & In-Memory Context**:
   - In `demos/wallet-transfer-demo/src/hooks/useTransfer.ts`, intercepted `TransferError` carrying a non-empty `burnTxHash`.
   - Captured the transfer context (`from`, `to`, `network`, `recipient`, `burnTxHash`, `attestationHash`) at submit time in `RecoverableTransferContext`.
2. **Interactive Recovery Panel (`ErrorBanner.tsx`)**:
   - Transformed the error banner into an interactive recovery panel when `recoverableBurnTxHash` is present.
   - Explains clearly that funds safely left the source chain and gives a direct link to the source-chain explorer.
   - Added a "Copy burn hash" button.
   - Added a "Complete transfer" recovery button that calls `completeMint()` using the captured destination parameters and destination wallet without re-burning.
   - Maintained standard retry banners for pre-burn failures and submission-uncertain timeouts.
3. **Context Binding in `App.tsx`**:
   - Tied `mintParams` and `destinationWalletConnected` to `recoverableTransfer.to` and `recoverableTransfer.network`, ensuring that switching form direction in the UI cannot misdirect the recovery call.
4. **Hermetic Test Suite**:
   - Verified in `tests/demo-recovery.test.ts`.

**Payout Wallet Address**: `0xC345C07229307d4f1c7935aD2cAe48e390215808`
