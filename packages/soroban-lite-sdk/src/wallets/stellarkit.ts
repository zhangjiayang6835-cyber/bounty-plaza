/**
 * soroban-lite-sdk — src/wallets/stellarkit.ts
 *
 * WalletAdapter implementation for Stellar Wallets Kit (@creit.tech/stellar-wallets-kit).
 *
 * @packageDocumentation
 */

import { SignTransactionOptions, WalletAdapter } from "./types";

/**
 * Minimal interface representing a StellarWalletsKit instance.
 */
export interface StellarWalletsKitInstance {
  openModal?: (options?: {
    modalTitle?: string;
    onWalletSelected?: (option: { id: string; [key: string]: unknown }) => void;
    [key: string]: unknown;
  }) => Promise<unknown> | unknown;
  setWallet?: (walletId: string) => void;
  getAddress?: () => Promise<{ address: string; [key: string]: unknown } | string>;
  getPublicKey?: () => Promise<string>;
  signTransaction?: (
    xdr: string,
    opts?: { networkPassphrase?: string; network?: string; accountToSign?: string; [key: string]: unknown }
  ) => Promise<{ signedTxXdr?: string; error?: string; [key: string]: unknown } | string>;
  [key: string]: unknown;
}

export interface StellarKitAdapterOptions {
  /**
   * An existing StellarWalletsKit instance.
   */
  kit?: StellarWalletsKitInstance;

  /**
   * Custom title displayed on the wallet connection modal.
   */
  modalTitle?: string;
}

/**
 * `StellarKitAdapter` wraps `@creit.tech/stellar-wallets-kit` to provide multi-wallet
 * connection and signing support.
 *
 * @example
 * ```ts
 * import { StellarKitAdapter } from "soroban-lite-sdk";
 * import { StellarWalletsKit, WalletNetwork, allowAllModules } from "@creit.tech/stellar-wallets-kit";
 *
 * const kit = new StellarWalletsKit({
 *   network: WalletNetwork.TESTNET,
 *   selectedWalletId: "freighter",
 *   modules: allowAllModules(),
 * });
 *
 * const adapter = new StellarKitAdapter({ kit });
 * const publicKey = await adapter.connect();
 * ```
 */
export class StellarKitAdapter implements WalletAdapter {
  readonly name = "StellarWalletsKit";
  private kit: StellarWalletsKitInstance | null;
  private modalTitle?: string;

  constructor(kitOrOptions?: StellarWalletsKitInstance | StellarKitAdapterOptions) {
    if (kitOrOptions && typeof (kitOrOptions as StellarWalletsKitInstance).signTransaction === "function") {
      this.kit = kitOrOptions as StellarWalletsKitInstance;
    } else if (kitOrOptions && typeof kitOrOptions === "object") {
      const opts = kitOrOptions as StellarKitAdapterOptions;
      this.kit = opts.kit || null;
      this.modalTitle = opts.modalTitle;
    } else {
      this.kit = null;
    }
  }

  /**
   * Checks whether Stellar Wallets Kit is initialized or accessible on the global window.
   */
  isAvailable(): boolean {
    if (this.kit && typeof this.kit.signTransaction === "function") {
      return true;
    }
    if (typeof window !== "undefined") {
      return Boolean((window as any).stellarWalletsKit);
    }
    return false;
  }

  /**
   * Resolves the active kit instance, falling back to window.stellarWalletsKit if available.
   */
  private resolveKit(): StellarWalletsKitInstance {
    if (this.kit && typeof this.kit.signTransaction === "function") {
      return this.kit;
    }
    if (typeof window !== "undefined" && (window as any).stellarWalletsKit) {
      this.kit = (window as any).stellarWalletsKit;
      return this.kit!;
    }
    throw new Error(
      "StellarKitAdapter: Stellar Wallets Kit is not available or initialized. Please supply a valid StellarWalletsKit instance in the constructor."
    );
  }

  /**
   * Connects via Stellar Wallets Kit, opening the modal if configured, and returns the connected public key.
   *
   * @throws `Error` if the kit is unavailable or connection fails.
   */
  async connect(): Promise<string> {
    const kit = this.resolveKit();

    try {
      // 1. Trigger modal if present
      if (typeof kit.openModal === "function") {
        await kit.openModal({
          modalTitle: this.modalTitle || "Connect a Stellar Wallet",
          onWalletSelected: (option: { id: string }) => {
            if (typeof kit.setWallet === "function" && option?.id) {
              kit.setWallet(option.id);
            }
          },
        });
      }

      // 2. Retrieve public address
      let addrRes: unknown;
      if (typeof kit.getAddress === "function") {
        addrRes = await kit.getAddress();
      } else if (typeof kit.getPublicKey === "function") {
        addrRes = await kit.getPublicKey();
      } else {
        throw new Error(
          "StellarKitAdapter: Stellar Wallets Kit instance does not implement `getAddress` or `getPublicKey`."
        );
      }

      if (typeof addrRes === "string" && addrRes.trim()) {
        return addrRes.trim();
      }

      if (typeof addrRes === "object" && addrRes !== null) {
        const resObj = addrRes as { address?: string; error?: string };
        if (resObj.error) {
          throw new Error(`StellarKitAdapter: Connection error — ${resObj.error}`);
        }
        if (resObj.address && typeof resObj.address === "string" && resObj.address.trim()) {
          return resObj.address.trim();
        }
      }

      throw new Error("StellarKitAdapter: Failed to retrieve valid public key from Stellar Wallets Kit.");
    } catch (error) {
      if ((error as Error).message.startsWith("StellarKitAdapter:")) {
        throw error;
      }
      throw new Error(`StellarKitAdapter: Connection failed — ${(error as Error).message}`);
    }
  }

  /**
   * Requests Stellar Wallets Kit to sign an XDR transaction envelope.
   *
   * @param xdr - Base64 XDR string of the transaction
   * @param opts - Signing options including networkPassphrase
   * @returns The signed transaction base64 XDR string
   * @throws `Error` if the kit is unavailable, user rejects, or signing fails.
   */
  async signTransaction(
    xdr: string,
    opts?: SignTransactionOptions
  ): Promise<string> {
    if (!xdr?.trim()) {
      throw new Error("StellarKitAdapter: `xdr` must be a non-empty string.");
    }

    const kit = this.resolveKit();

    if (typeof kit.signTransaction !== "function") {
      throw new Error(
        "StellarKitAdapter: Stellar Wallets Kit instance does not export `signTransaction` method."
      );
    }

    try {
      const signRes = await kit.signTransaction(xdr.trim(), {
        networkPassphrase: opts?.networkPassphrase,
        network: opts?.network,
        accountToSign: opts?.accountToSign,
        ...opts,
      });

      if (typeof signRes === "string" && signRes.trim()) {
        return signRes.trim();
      }

      if (typeof signRes === "object" && signRes !== null) {
        const resObj = signRes as { signedTxXdr?: string; error?: string };
        if (resObj.error) {
          throw new Error(`StellarKitAdapter: Signing rejected or failed — ${resObj.error}`);
        }
        if (resObj.signedTxXdr && typeof resObj.signedTxXdr === "string" && resObj.signedTxXdr.trim()) {
          return resObj.signedTxXdr.trim();
        }
      }

      throw new Error("StellarKitAdapter: Stellar Wallets Kit returned an invalid or empty signature response.");
    } catch (error) {
      if ((error as Error).message.startsWith("StellarKitAdapter:")) {
        throw error;
      }
      throw new Error(`StellarKitAdapter: Transaction signing failed — ${(error as Error).message}`);
    }
  }
}
