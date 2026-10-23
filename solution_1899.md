# Fix for Issue #1899: Docs: add a "Failure modes and recovery" guide

## Problem
Developers integrating the Parabola cross-chain bridge SDK previously had to reverse-engineer error recovery by inspecting source code. Crucial concepts—such as preserving `burnTxHash` across `TransferError`, retrying `completeMint` after an attestation timeout without double-burning, distinguishing safe retryable states from uncertain submission timeouts, handling persistent Circle Iris 5xx outages, and selecting suitable `pollTimeout` values—were missing from high-level documentation.

## Solution
1. **Transfer Lifecycle Documentation**:
   - Documented the three sequential, durable stages: Source Burn → Iris Attestation → Destination Mint.
   - Clarified that once the source burn is confirmed on-chain, funds have left the source balance and **must never be re-burned**.
2. **Error Classification Matrix**:
   - Categorized every exported error class (`TransferError`, `AttestationNotReadyError`, `IrisRequestError`, `SubmissionTimeoutError`, `AmountPrecisionError`).
   - Distinctly separated "Funds are safe; retryable" from "Outcome unknown; inspect first".
3. **Worked Code Examples**:
   - Added end-to-end TypeScript examples demonstrating `TransferError` interception, persistence, delay, and execution of `completeMint()`.
   - Provided separate worked examples for both **Arc → Stellar** (using `StellarSigner`) and **Stellar → Arc** (using `ArcSigner`).
4. **Configuration Guidance**:
   - Provided pragmatic rules for configuring `pollTimeout` (e.g. 60s for serverless/API gateways vs 300s for background workers) and `pollInterval`.
5. **Hermetic Test Suite**:
   - Added `tests/failure-recovery-guide.test.ts` verifying the documentation's structure, complete error class coverage, and code examples.

**Payout Wallet Address**: `0xC345C07229307d4f1c7935aD2cAe48e390215808`
