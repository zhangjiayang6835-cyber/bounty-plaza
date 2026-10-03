# soroban-lite-sdk

A lightweight SDK for building on Soroban.

## Installation

```bash
npm install soroban-lite-sdk
```

## Usage

```typescript
import { SorobanClient } from "soroban-lite-sdk";

const client = new SorobanClient({
  rpcUrl: "https://soroban-testnet.stellar.org",
});

const simulated = await client.simulate(txXDR);
const submitted = await client.submit(signedTxXDR);
```

## Wallet Integration

This SDK provides first-class wallet adapter support for **Freighter** and **Stellar Wallets Kit**.

### Adapters

- `FreighterAdapter` — uses `@stellar/freighter-api`
- `StellarKitAdapter` — uses `@creit.tech/stellar-wallets-kit`

Both adapters implement the `WalletAdapter` interface:

```typescript
interface WalletAdapter {
  readonly name: string;
  isAvailable(): boolean;
  connect(): Promise<string>;
  signTransaction(xdr: string, opts?: { networkPassphrase?: string }): Promise<string>;
}
```

### Using signAndSubmit

```typescript
import { SorobanClient, FreighterAdapter } from "soroban-lite-sdk";

const client = new SorobanClient();
const wallet = new FreighterAdapter();

if (!wallet.isAvailable()) {
  throw new Error("Freighter is not installed");
}

const address = await wallet.connect();
const result = await client.signAndSubmit(txXDR, wallet);
```

### Peer Dependencies

The wallet packages are peer dependencies and must be installed separately:

```bash
# For Freighter support
npm install @stellar/freighter-api

# For Stellar Wallets Kit support
npm install @creit.tech/stellar-wallets-kit
```

## Testing

```bash
npm test
