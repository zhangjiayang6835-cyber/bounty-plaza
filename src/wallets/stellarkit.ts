import type {
  WalletAdapter,
  SignTransactionOptions,
} from "./types.ts";
import {
  WalletNotInstalledError,
  WalletConnectionError,
  WalletSigningError,
} from "./types.ts";

export interface StellarWalletsKitInstance {
  openModal(options?: Record<string, unknown>): Promise<void>;
  getPublicKey(): Promise<string>;
  signTransaction(
    xdr: string,
    opts?: { networkPassphrase?: string; accountToSign?: string }
  ): Promise<{ signedXDR?: string } | string>;
  setWallet?: (walletId: string) => void;
}

export class StellarKitAdapter implements WalletAdapter {
  readonly name = "StellarWalletsKit";
  private kit?: StellarWalletsKitInstance;

  constructor(customKit?: StellarWalletsKitInstance) {
    this.kit = customKit;
  }

  private async getKit(): Promise<StellarWalletsKitInstance> {
    if (this.kit) return this.kit;
    try {
      // Dynamic import to satisfy peerDependency contract
      const kitModule = await import("@creit.tech/stellar-wallets-kit");
      const KitClass = kitModule.StellarWalletsKit || kitModule.default;
      if (!KitClass) {
        throw new WalletNotInstalledError(this.name);
      }
      return new KitClass() as StellarWalletsKitInstance;
    } catch {
      if (typeof window !== "undefined" && (window as unknown as { stellarWalletsKit?: StellarWalletsKitInstance }).stellarWalletsKit) {
        return (window as unknown as { stellarWalletsKit: StellarWalletsKitInstance }).stellarWalletsKit;
      }
      throw new WalletNotInstalledError(this.name);
    }
  }

  isAvailable(): boolean {
    if (this.kit) return true;
    if (typeof window !== "undefined" && (window as unknown as { stellarWalletsKit?: unknown }).stellarWalletsKit) {
      return true;
    }
    return false;
  }

  async connect(): Promise<string> {
    const kit = await this.getKit();
    try {
      if (kit.openModal) {
        await kit.openModal();
      }
      const publicKey = await kit.getPublicKey();
      if (!publicKey) {
        throw new Error("No public key returned by StellarWalletsKit");
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
    const kit = await this.getKit();
    try {
      const result = await kit.signTransaction(xdr, {
        networkPassphrase: opts?.networkPassphrase,
        accountToSign: opts?.accountToSign,
      });

      if (!result) {
        throw new Error("Transaction signing rejected or empty response");
      }

      if (typeof result === "string") {
        return result;
      }

      if (result.signedXDR) {
        return result.signedXDR;
      }

      throw new Error("Invalid signed XDR format returned from StellarWalletsKit");
    } catch (err: unknown) {
      if (err instanceof WalletNotInstalledError) {
        throw err;
      }
      const msg = err instanceof Error ? err.message : String(err);
      throw new WalletSigningError(this.name, msg);
    }
  }
}
