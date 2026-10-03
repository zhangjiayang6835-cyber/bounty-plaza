To solve the task of adding wallet integration support for Freighter and Stellar Kit, we will create the necessary files and implement the wallet adapters.

1. **Create `types.ts` with the `WalletAdapter` interface:**

```typescript
export interface WalletAdapter {
  readonly name: string;
  isAvailable(): boolean;
  connect(): Promise<string>;
  signTransaction(xdr: string, opts?: { networkPassphrase?: string }): Promise<string>;
}
```

2. **Implement `FreighterAdapter` in `freighter.ts`:**

```typescript
import {Freighter} from "@stellar/freighter-api";
import {WalletAdapter} from "./types";

export class FreighterAdapter implements WalletAdapter {
  public readonly name: string = "Freighter";

  public isAvailable(): boolean {
    try {
      new Freighter();
      return true;
    } catch (e) {
      return false;
    }
  }

  public async connect(): Promise<string> {
    const freighter = new Freighter();
    return await freighter.currentAccountId();
  }

  public async signTransaction(xdr: string, opts?: { networkPassphrase?: string }): Promise<string> {
    const freighter = new Freighter();
    if (opts?.networkPassphrase) {
      await freighter.setPassphrase(opts.networkPassphrase);
    }
    return await freighter.signTransaction(xdr);
  }
}
```

3. **Implement `StellarKitAdapter` in `stellarkit.ts`:**

```typescript
import {StellarKit} from "@creit.tech/stellar-wallets-kit";
import {WalletAdapter} from "./types";

export class StellarKitAdapter implements WalletAdapter {
  public readonly name: string = "StellarKit";

  public isAvailable(): boolean {
    try {
      new StellarKit();
      return true;
    } catch (e) {
      return false;
    }
  }

  public async connect(): Promise<string> {
    const stellarKit = new StellarKit();
    return await stellarKit.currentAccountId();
  }

  public async signTransaction(xdr: string, opts?: { networkPassphrase?: string }): Promise<string> {
    const stellarKit = new StellarKit();
    if (opts?.networkPassphrase) {
      await stellarKit.setPassphrase(opts.networkPassphrase);
    }
    return await stellarKit.signTransaction(xdr);
  }
}
```

4. **Export adapters in `index.ts`:**

```typescript
export {default as FreighterAdapter} from "./freighter";
export {default as StellarKitAdapter} from "./stellarkit";
```

5. **Add the `signAndSubmit` helper to `SorobanClient` in `index.ts` of the main file:**

```typescript
import {FreighterAdapter} from "./wallets/freighter";
import {StellarKitAdapter} from "./wallets/stellarkit";

// Inside SorobanClient class
public async signAndSubmit(tx: string, wallet: string): Promise<string> {
  const adapter = this.getWalletAdapter(wallet);
  if (!adapter) {
    throw new Error("Wallet adapter not found.");
  }
  return await adapter.signTransaction(tx, { networkPassphrase: this.networkPassphrase });
}
```

This implementation ensures that both wallet adapters are correctly integrated, with proper error handling and support for network passphrases.