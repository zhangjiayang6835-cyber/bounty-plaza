import type {
  WalletAdapter,
  SignTransactionOptions,
} from "./types.ts";
import {
  WalletNotInstalledError,
  WalletConnectionError,
  WalletSigningError,
} from "./types.ts";

export interface FreighterApi {
  isConnected(): Promise<boolean> | boolean;
  getPublicKey(): Promise<string>;
  signTransaction(
    xdr: string,
    opts?: { networkPassphrase?: string; accountToSign?: string }
  ): Promise<string>;
}

export class FreighterAdapter implements WalletAdapter {
  readonly name = "Freighter";
  private api?: FreighterApi;

  constructor(customApi?: FreighterApi) {
    this.api = customApi;
  }

  private async getApi(): Promise<FreighterApi> {
    if (this.api) return this.api;
    try {
      // Dynamic import to satisfy peerDependency contract
      const freighter = await import("@stellar/freighter-api");
      return (freighter.default || freighter) as unknown as FreighterApi;
    } catch {
      // Check global window fallback
      if (typeof window !== "undefined" && (window as unknown as { freighter?: FreighterApi }).freighter) {
        return (window as unknown as { freighter: FreighterApi }).freighter;
      }
      throw new WalletNotInstalledError(this.name);
    }
  }

  isAvailable(): boolean {
    if (this.api) return true;
    if (typeof window !== "undefined" && (window as unknown as { freighter?: unknown }).freighter) {
      return true;
    }
    return false;
  }

  async connect(): Promise<string> {
    const api = await this.getApi();
    try {
      const connected = await api.isConnected();
      if (!connected) {
        throw new WalletNotInstalledError(this.name);
      }
      const publicKey = await api.getPublicKey();
      if (!publicKey) {
        throw new Error("No public key returned by Freighter");
      }
      return publicKey;
    } catch (err: unknown) {
      if (err instanceof WalletNotInstalledError) {
        throw err;
      }
      const msg = err instanceof Error ? err.message : String(err);
      throw new WalletConnectionError(this.name, msg);
    }
  }

  async signTransaction(xdr: string, opts?: SignTransactionOptions): Promise<string> {
    const api = await this.getApi();
    try {
      const signedXdr = await api.signTransaction(xdr, {
        networkPassphrase: opts?.networkPassphrase,
        accountToSign: opts?.accountToSign,
      });
      if (!signedXdr) {
        throw new Error("Transaction signing rejected or returned empty XDR");
      }
      return signedXdr;
    } catch (err: unknown) {
      if (err instanceof WalletNotInstalledError) {
        throw err;
      }
      const msg = err instanceof Error ? err.message : String(err);
      throw new WalletSigningError(this.name, msg);
    }
  }
}
