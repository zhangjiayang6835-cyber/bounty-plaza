# Integrating Parabola

## Who this guide is for

The [README](README.md) covers installation and one-off scripts: import `transfer()`, build a
signer, call it, done. This guide is different: it's for wiring Parabola into a persistent
application, backend service or browser app, where the concerns are different: where do keys
live, what happens when a call fails partway through, and how do you resume a transfer that
didn't finish. If you haven't read the README yet, start there; this guide assumes you have.

## Two integration patterns

### Pattern A: backend-held keys

**When to use:** your service already custodies a hot wallet key server-side for one or both
chains, e.g. an operational treasury wallet, a relayer, anything where the key already lives in
your infrastructure rather than a user's wallet.

**Shape:** build a signer once from an env-stored private key, call `transfer()` from an API
route or background job. This is exactly what [`examples/arc-to-stellar.ts`](examples/arc-to-stellar.ts)
and [`examples/stellar-to-arc.ts`](examples/stellar-to-arc.ts) already show; read those as the
base pattern for this approach.

### Pattern B: non-custodial browser wallet (recommended for user-facing apps)

**When to use:** end users connect their own wallets and your app never touches a private key.

**Shape:**

- `ArcSigner` just wraps a viem `WalletClient`. Build one from an injected wallet with
  `createWalletClient({ account, chain: arcMainnetChain, transport: custom(window.ethereum) })`
  and you have a valid `ArcSigner` (use `arcTestnetChain` for testnet). Nothing Parabola-specific about it.
- `StellarSigner` accepts a `signTransaction` callback instead of a raw `Keypair` for exactly
  this case. Freighter's own `signTransaction(xdr, opts)` resolves to
  `{ signedTxXdr: string; signerAddress: string; error?: FreighterApiError }` (note it's an
  **object**, not a plain string, and it never throws; check `.error` on every call). Your
  callback just needs to unwrap `.signedTxXdr`.

**Reference:** [`demos/wallet-transfer-demo/`](demos/wallet-transfer-demo) is the full working
example of this pattern, specifically
[`src/lib/arcWallet.ts`](demos/wallet-transfer-demo/src/lib/arcWallet.ts) and
[`src/lib/stellarWallet.ts`](demos/wallet-transfer-demo/src/lib/stellarWallet.ts).

## Failure modes and recovery

### Transfer lifecycle

A transfer has three durable stages: burn on the source chain, attestation by Circle's Iris
service, and mint on the destination chain. Before the burn is confirmed, a failure means no
recoverable burn is known. After confirmation, the source funds have already left the source
chain; preserve the burn transaction hash, wait for attestation if necessary, then call
`completeMint()` with a destination-chain signer. Once the mint is confirmed, record its hash
and do not submit the same CCTP message again.

### Exported error classes

Branch on classes and `TransferError.code`, never message text.

| Error | What it means for funds | Recommended action |
| --- | --- | --- |
| `TransferError` | The source burn succeeded, but attestation polling or minting failed. `burnTxHash` identifies the recoverable burn; `attestationHash` is present if attestation was already retrieved. | Persist the hashes. Wait if `code === "ATTESTATION_NOT_READY"`; otherwise diagnose the cause, then resume with `completeMint()`. Do not burn again. |
| `AttestationNotReadyError` | **Funds are safe; retry.** The burn is confirmed but Circle has not attested it yet. | Wait, then retry `completeMint()` (or the relevant read). |
| `IrisRequestError` | The Circle-side lookup failed; it does not establish that the burn or mint failed. `status` contains the HTTP status when available. | Treat Iris as an unavailable upstream, back off, and retry the lookup or recovery call. Preserve the burn hash. |
| `SubmissionTimeoutError` | **Outcome unknown; inspect first.** A transaction was broadcast and `hash` identifies it, but confirmation was not observed before timeout. | Check that hash on the relevant chain before retrying. Never assume nothing was submitted. |

A `404` from Iris during polling is an ordinary not-yet-indexed state and polling continues. A
persistent Iris failure instead surfaces as `IrisRequestError` (after five consecutive failures),
so an upstream outage remains distinct from a slow attestation.

### Recover after `TransferError`

This complete example records the burn, waits, and completes the mint without creating a second
burn:

```typescript
import { completeMint, transfer, TransferError } from "@asctp/parabola";

try {
  await transfer(params);
} catch (error) {
  if (!(error instanceof TransferError)) throw error;

  await ledger.record({
    from: params.from,
    to: params.to,
    burnTxHash: error.burnTxHash,
    network: params.network ?? "mainnet",
  });

  // Replace this with a durable retry queue in a service.
  await new Promise((resolve) => setTimeout(resolve, 30_000));

  const recovered = await completeMint({
    from: params.from,
    to: params.to,
    burnTxHash: error.burnTxHash,
    network: params.network,
    signer: destinationSigner,
  });

  await ledger.markComplete(error.burnTxHash, recovered.mintTxHash);
}
```

Use the signer native to the destination:

```typescript
// Arc -> Stellar: destinationSigner is a StellarSigner
await completeMint({
  from: "arc",
  to: "stellar",
  burnTxHash,
  network: "mainnet",
  signer: stellarSigner,
});

// Stellar -> Arc: destinationSigner is an ArcSigner
await completeMint({
  from: "stellar",
  to: "arc",
  burnTxHash,
  network: "mainnet",
  signer: arcSigner,
});
```

`completeMint()` performs the Stellar recipient readiness check when Stellar is the destination.
It does not deduplicate submissions, so keep a ledger keyed by `(burnTxHash, network)` and return
the recorded mint hash for repeated requests.

### Choosing `pollTimeout`

`pollTimeout` limits how long one SDK call waits; it does not cancel the burn or attestation.
The default is 300,000 ms. Keep it long enough for normal finality and attestation latency when a
worker can remain open. Use a shorter value for latency-bounded HTTP requests, persist the burn
hash, and continue recovery asynchronously. A timeout after a confirmed burn is **funds safe,
retry**; a `SubmissionTimeoutError` remains **outcome unknown, inspect first**.

Choose `pollInterval` separately (default 3,000 ms): shorter intervals increase Iris traffic but
do not make Circle attest sooner. Add retry backoff outside the SDK for repeated recovery jobs.

```typescript
await completeMint({
  from,
  to,
  burnTxHash,
  signer: destinationSigner,
  network,
  options: {
    pollInterval: 3_000,
    pollTimeout: 60_000,
  },
});
```

## Completing a burn your service did not create

`completeMint()` does not require the burn to have come from this process, or from Parabola at all. It takes `from`, `to`, `burnTxHash`, `network` and a signer for the destination chain, and it keeps no record of burns, so it neither requires nor checks that your service produced the original `transfer()` call. This is the shape a relayer needs.

Read the burn before you spend anything on it. `resolveBurn` returns what the burn already committed to:

```typescript
import { resolveBurn } from "@asctp/parabola";

const burn = await resolveBurn({ from, burnTxHash, network });
// burn.forwardRecipient is the Stellar account the mint will pay, on an arc -> stellar burn
// burn.amountRaw is in the source chain's USDC subunits, 10^6 on Arc
// burn.attestation is null while Circle is still signing
```

`resolveBurn` returns as soon as Iris has indexed the burn, which is before Circle signs, so a populated `forwardRecipient` alongside a null `attestation` is the normal state for the first seconds after a burn. It throws `AttestationNotReadyError` if Iris has not indexed the burn at all yet.

For a service that must answer its own caller immediately rather than holding the request open, `getAttestation` is a single non-blocking read instead of a poll to a deadline:

```typescript
import { getAttestation, AttestationNotReadyError } from "@asctp/parabola";

try {
  const message = await getAttestation({ sourceDomain: 26, transactionHash: burnTxHash, useSandbox: false });
  if (message.status !== "complete" || !message.attestation) {
    return respond(409, { retryable: true });
  }
  // message.message and message.attestation are ready to submit
} catch (err) {
  if (err instanceof AttestationNotReadyError) return respond(409, { retryable: true });
  throw err;
}
```

The Stellar recipient check `transfer()` performs is built into `completeMint()` as well, and it reads the account out of the burn message's forward hook rather than accepting a recipient argument. A relayer therefore cannot accidentally preflight a different account than the one that gets paid.

### Idempotency is yours to enforce

Nothing in Parabola dedupes, and `completeMint()` will submit again for a burn that was already minted. The chain rejects the re-used CCTP message, so no funds move, but you pay gas to learn that.

Keep a ledger keyed on `(burn hash, network)` and return the recorded mint transaction hash for a repeated request instead of resubmitting. A relayer is precisely the caller that retries, so this is a required component rather than a nicety.

## Network selection in a service

`network` is optional everywhere and defaults to `"mainnet"`. That is convenient for a script and is the wrong failure mode for a long-running process holding a funded key, because an omitted field silently spends real USDC.

Default your own configuration to testnet, make mainnet explicit, and reject any request whose `network` disagrees with the operator's choice. That way a caller cannot push the service onto a network the operator did not select.

## Recovering from a "pending" result: destinationSigner and completeMint

This is a different, sanctioned recovery path from the one above: use it when you deliberately
didn't attach `options.destinationSigner` (for example, your backend only holds the source
chain's key at call time). `transfer()` performs the burn and attestation polling, then returns
`status: "pending"` with a populated `burnTxHash` and an empty `mintTxHash`. `completeMint()`
finishes it later, given that `burnTxHash`.

**Persistence requirement this guide adds:** if your backend could restart between the initial
`transfer()` call and calling `completeMint()`, persist `{ from, to, burnTxHash, network }` to
durable storage before you return from the first call. `CompleteMintParams` requires those as
input, and unlike a failure thrown mid-flight, this is a hash Parabola *does* hand back to you,
so don't let it evaporate in memory. Store `network` alongside it: it decides which Iris
environment and which contract addresses the later call uses, and guessing it wrong on recovery
is silent.

**Reference:**
[`src/components/TransferStatus.tsx`](demos/wallet-transfer-demo/src/components/TransferStatus.tsx)'s
"Complete mint" button is the interactive version of this recovery path.

## Running the demo app locally

```bash
pnpm install
pnpm build      # builds @asctp/parabola: required first, see demos/wallet-transfer-demo/README.md
pnpm dev:wallet-transfer-demo
```

Prerequisites: MetaMask and Freighter browser extensions, and funded Arc + Stellar accounts. On
testnet, fund both via [faucet.circle.com](https://faucet.circle.com). Both integration patterns
above are reachable in the same UI: check or uncheck "Complete the mint automatically" to switch
between them.

## Choosing a pattern for your app

No user-key custody at all, ever -> Pattern B. Already have an operational wallet funded and
ready to sign -> Pattern A is simpler, one fewer moving part. Nothing stops a single application
from using both for different flows (e.g. Pattern A for automated payouts, Pattern B for
user-initiated transfers).
