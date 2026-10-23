# Failure Modes and Recovery Guide

## Overview

Moving native USDC across chains via Circle CCTP involves asynchronous coordination across three independent systems: the source chain, Circle's off-chain Iris attestation service, and the destination chain.

Understanding failure modes and handling errors correctly is critical to avoid double-spends and orphaned transactions.

---

## Transfer Lifecycle

A cross-chain transfer proceeds through three durable stages:

```
[1. Source Chain Burn] ---> [2. Circle Iris Attestation] ---> [3. Destination Chain Mint]
```

1. **Source Chain Burn**:
   - The user's USDC is burned on the source chain (Arc or Stellar).
   - If this stage fails, no funds have left the user's balance. The operation can be retried or aborted safely.
   - Once confirmed, the burn is immutable and the `burnTxHash` is emitted.

2. **Circle Iris Attestation**:
   - Circle's Iris service observes the source burn event and generates an authorized cryptographic attestation signature.
   - Attestation typically completes within minutes (depending on finality).
   - During this stage, funds are in flight and safe. **Never initiate another burn**, as doing so would cause a double-spend.

3. **Destination Chain Mint**:
   - The attestation signature and CCTP message are submitted to the destination chain's MessageTransmitter to mint native USDC to the recipient.
   - If the mint transaction fails or times out, the transfer can be resumed at any time using `completeMint()`.

---

## Exported Error Classes and Recommended Actions

Always branch on explicit error classes or `TransferError.code`, never on message strings.

| Error Class | State of Funds | Meaning & Recommended Action |
|:---|:---|:---|
| **`TransferError`** | **Burn confirmed; funds left source chain** | The source burn succeeded, but attestation polling or destination minting encountered an error. Contains `burnTxHash` (and `attestationHash` if obtained). **Do not burn again.** Inspect `code`: if `ATTESTATION_NOT_READY`, wait and retry. Otherwise, resolve with `completeMint()`. |
| **`AttestationNotReadyError`** | **Funds are safe; retryable** | The burn is confirmed on-chain, but Circle has not yet signed the attestation. Wait (e.g. 15-30s) and retry attestation retrieval or `completeMint()`. |
| **`IrisRequestError`** | **External API issue; retry with backoff** | Circle's Iris service returned a non-200 HTTP response or network failure. This does not indicate failure of funds or contracts. Treat as temporary upstream downtime, apply exponential backoff, and retry. |
| **`SubmissionTimeoutError`** | **Outcome unknown; inspect first** | A transaction was broadcast and has a valid `hash`, but confirmation was not observed before the client-side timeout expired. **Do not retry blindly.** Inspect the transaction hash on an explorer or RPC node to verify whether it succeeded or failed before taking action. |
| **`AmountPrecisionError`** | **Pre-flight validation failed; safe** | Thrown prior to any approve or burn when the requested amount has more decimal places than the destination chain supports (e.g. Arc supports 6 decimals, Stellar supports 7). Safe to modify user input and retry. |

---

## Worked Recovery Examples with `completeMint`

When a transfer fails post-burn, catch `TransferError` and use `completeMint()` to finish minting without re-burning.

### 1. General Recovery Pattern
```typescript
import { transfer, completeMint, TransferError } from "@asctp/parabola";

try {
  await transfer(params);
} catch (error) {
  if (error instanceof TransferError) {
    console.warn(`Post-burn failure detected. Burn tx: ${error.burnTxHash}`);
    
    // Save burnTxHash to persistent storage / database
    await db.savePendingTransfer({
      burnTxHash: error.burnTxHash,
      from: params.from,
      to: params.to,
      recipient: params.recipient,
      network: params.network ?? "mainnet",
    });

    // Wait for Iris attestation finality
    await new Promise((r) => setTimeout(r, 30_000));

    // Resume and finish the mint
    const recovered = await completeMint({
      from: params.from,
      to: params.to,
      burnTxHash: error.burnTxHash,
      network: params.network,
      signer: destinationSigner,
    });

    console.log(`Successfully completed transfer. Mint tx: ${recovered.mintTxHash}`);
  } else {
    // Pre-burn failure: funds never left source chain
    console.error("Transfer failed before burn was confirmed:", error);
  }
}
```

### 2. Arc → Stellar Recovery
When transferring from Arc to Stellar, the destination signer must be a `StellarSigner`:

```typescript
import { completeMint } from "@asctp/parabola";

const result = await completeMint({
  from: "arc",
  to: "stellar",
  burnTxHash: "0x1234567890abcdef...",
  network: "mainnet",
  signer: stellarSigner, // Destination Stellar Keypair or Freighter
});
console.log("Minted on Stellar:", result.mintTxHash);
```

### 3. Stellar → Arc Recovery
When transferring from Stellar to Arc, the destination signer must be an `ArcSigner`:

```typescript
import { completeMint } from "@asctp/parabola";

const result = await completeMint({
  from: "stellar",
  to: "arc",
  burnTxHash: "a1b2c3d4e5f6...", // 64-char hex Stellar transaction hash
  network: "mainnet",
  signer: arcSigner, // Destination Viem WalletClient
});
console.log("Minted on Arc:", result.mintTxHash);
```

---

## Guidance on Choosing `pollTimeout` and `pollInterval`

- **`pollTimeout`** (default: 300,000 ms / 5 minutes):
  - Limits how long the SDK will actively wait for Circle attestation and destination minting.
  - Setting a shorter `pollTimeout` (e.g. 60,000 ms) is useful for web servers or lambda functions with tight execution deadlines.
  - Reaching `pollTimeout` throws a `TransferError` with `code: "ATTESTATION_NOT_READY"` and preserves `burnTxHash`.
- **`pollInterval`** (default: 3,000 ms):
  - Frequency of polling Iris for attestation readiness.
  - Polling faster than 2,000 ms is discouraged to prevent hitting Circle API rate limits.
