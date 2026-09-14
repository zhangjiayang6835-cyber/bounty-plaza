# soroban-lite-sdk

A lightweight, strongly-typed TypeScript SDK for interacting with Soroban smart contracts on the Stellar network with native wallet integration support for Freighter and Stellar Wallets Kit.

[![npm version](https://img.shields.io/npm/v/soroban-lite-sdk.svg)](https://www.npmjs.com/package/soroban-lite-sdk)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Installation

```bash
npm install soroban-lite-sdk @stellar/stellar-sdk
```

### Optional Wallet Dependencies

If you plan to use wallet adapters in the browser:

```bash
# For Freighter wallet support
npm install @stellar/freighter-api

# For multi-wallet support via Stellar Wallets Kit
npm install @creit.tech/stellar-wallets-kit
```

---

## Quick Start

```typescript
import { SorobanClient, FreighterAdapter } from "soroban-lite-sdk";

// 1. Initialize client using named preset
const client = new SorobanClient({ network: "TESTNET" });

// 2. Connect Freighter wallet
const freighter = new FreighterAdapter();
if (freighter.isAvailable()) {
  const userPublicKey = await freighter.connect();
  console.log("Connected account:", userPublicKey);
}

// 3. Simulate, sign with Freighter, submit, and poll in one step
const receipt = await client.signAndSubmit(myTransaction, freighter, {
  maxAttempts: 15,
  delayMs: 1_500,
  exponentialBackoff: true,
});

console.log("Final status:", receipt.status); // "SUCCESS" | "FAILED"
```

---

## Wallet Integration

`soroban-lite-sdk` provides a unified `WalletAdapter` interface and ready-to-use adapters for browser wallets.

### `WalletAdapter` Interface

```typescript
export interface WalletAdapter {
  readonly name: string;
  isAvailable(): boolean;
  connect(): Promise<string>;
  signTransaction(xdr: string, opts?: SignTransactionOptions): Promise<string>;
}
```

### 1. Freighter Adapter

Wraps `@stellar/freighter-api`.

```typescript
import { SorobanClient, FreighterAdapter } from "soroban-lite-sdk";

const client = new SorobanClient({ network: "TESTNET" });
const freighter = new FreighterAdapter();

// Check if extension is installed
if (!freighter.isAvailable()) {
  alert("Please install Freighter extension: https://www.freighter.app/");
}

// Connect and request public key
const address = await freighter.connect();

// Sign and submit a transaction directly
const result = await client.signAndSubmit(tx, freighter);
```

### 2. Stellar Wallets Kit Adapter

Wraps `@creit.tech/stellar-wallets-kit` for modal-based wallet selection (supporting Freighter, xBull, Albedo, Hana, Rabet, Ledger, etc.).

```typescript
import { SorobanClient, StellarKitAdapter } from "soroban-lite-sdk";
import { StellarWalletsKit, WalletNetwork, allowAllModules } from "@creit.tech/stellar-wallets-kit";

const kit = new StellarWalletsKit({
  network: WalletNetwork.TESTNET,
  selectedWalletId: "freighter",
  modules: allowAllModules(),
});

const adapter = new StellarKitAdapter({ kit, modalTitle: "Connect to DApp" });
const client = new SorobanClient({ network: "TESTNET" });

// Connect (opens wallet selection modal)
const publicKey = await adapter.connect();

// Sign and submit
const receipt = await client.signAndSubmit(tx, adapter);
```

### 3. `signAndSubmit` Lifecycle Helper

`SorobanClient.prototype.signAndSubmit(tx, wallet, options)` automates the complete 4-step execution flow:
1. **Simulate**: Calls `simulateTransaction(tx)` to verify execution and fee estimates.
2. **Sign**: Calls `wallet.signTransaction(xdr, { networkPassphrase })`.
3. **Submit**: Submits the signed transaction to the RPC node via `rpcServer.sendTransaction`.
4. **Poll**: Polls the RPC using `pollTransactionStatus(hash, options)` until `SUCCESS` or `FAILED`.

---

## API Reference

### SorobanClient

```typescript
new SorobanClient(config: SorobanConfig)
```

Accepts one of two config shapes:

```typescript
// Named preset
{ network: "TESTNET" | "MAINNET" | "FUTURENET" }

// Custom endpoint
{ rpcUrl: string; networkPassphrase: string }
```

**Methods**

- `simulateTransaction(tx)`: Simulates execution without submitting to network.
- `pollTransactionStatus(hash, options)`: Polls transaction status until terminal state.
- `signAndSubmit(tx, wallet, options)`: Simulates, signs via wallet adapter, submits, and polls.
- `getAccount(publicKey)`: Fetches account sequence and data.
- `getLatestLedger()`: Returns latest closed ledger.

---

## Testing & Quality

```bash
npm test              # Run unit tests via Vitest
npm run test:coverage # Run test suite with V8 coverage
npm run build         # Compile TypeScript
npm run typecheck     # Type validation
```

---

## Changelog

See [CHANGELOG.md](./CHANGELOG.md) for full version history.

---

## License

Released under the [MIT License](./LICENSE). © 2024 Soroban Lite SDK Contributors.
