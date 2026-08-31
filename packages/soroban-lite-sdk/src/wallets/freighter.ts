/**
 * soroban-lite-sdk — src/wallets/freighter.ts
 *
 * WalletAdapter implementation for Freighter wallet (@stellar/freighter-api).
 *
 * @packageDocumentation
 */

import * as freighterApiModule from "@stellar/freighter-api";
import { SignTransactionOptions, WalletAdapter } from "./types";

/**
 * Shape of the Freighter API module or injected window.freighter object.
 */
export interface FreighterApiInterface {
  isConnected?: () => Promise<boolean | { isConnected: boolean }> | boolean | { isConnected: boolean };
  isAllowed?: () => Promise<boolean | { isAllowed: boolean }> | boolean | { isAllowed: boolean };
  setAllowed?: () => Promise<boolean | { isAllowed: boolean }> | boolean | { isAllowed: boolean };
  requestAccess?: () => Promise<string | { address?: string; error?: string }>;
  getPublicKey?: () => Promise<string | { address?: string; error?: string }>;
  signTransaction?: (
    xdr: string,
    opts?: { networkPassphrase?: string; network?: string; accountToSign?: string; [key: string]: unknown }
  ) => Promise<string | { signedTxXdr?: string; error?: string }>;
  [key: string]: unknown;
}

export interface FreighterAdapterOptions {
  /**
   * Optional custom Freighter API object. Useful for testing or dependency injection.
   */
  api?: FreighterApiInterface;
}

/**
 * `FreighterAdapter` wraps the official Freighter browser extension API (`@stellar/freighter-api`).
 *
 * @example
 * ```ts
 * import { FreighterAdapter } from "soroban-lite-sdk";
 *
 * const freighter = new FreighterAdapter();
 * if (freighter.isAvailable()) {
 *   const publicKey = await freighter.connect();
 *   console.log("Connected account:", publicKey);
 * }
 * ```
 */
export class FreighterAdapter implements WalletAdapter {
  readonly name = "Freighter";
  private readonly api: FreighterApiInterface;

  constructor(options?: FreighterAdapterOptions) {
    this.api = (options?.api || freighterApiModule) as FreighterApiInterface;
  }

  /**
   * Synchronously checks whether Freighter is available in the current environment.
   */
  isAvailable(): boolean {
    if (typeof window !== "undefined") {
      const win = window as any;
      if (win.freighter || win.freighterApi) {
        return true;
      }
    }
    return typeof this.api?.isConnected === "function" || typeof this.api?.signTransaction === "function";
  }

  /**
   * Connects to Freighter, requests permission, and returns the connected public key.
   *
   * @throws `Error` if Freighter extension is not installed or connection is rejected.
   */
  async connect(): Promise<string> {
    if (!this.isAvailable()) {
      throw new Error(
        "FreighterAdapter: Freighter wallet extension is not installed or available. Please install Freighter from https://www.freighter.app/"
      );
    }

    try {
      // 1. Verify connection status if isConnected method exists
      if (typeof this.api.isConnected === "function") {
        const isConnRes = await this.api.isConnected();
        const connected =
          typeof isConnRes === "object" && isConnRes !== null && "isConnected" in isConnRes
            ? (isConnRes as { isConnected: boolean }).isConnected
            : Boolean(isConnRes);

        if (!connected) {
          throw new Error(
            "FreighterAdapter: Freighter wallet extension is not installed or accessible."
          );
        }
      }

      // 2. Request user authorization and public key
      let keyResult: unknown;
      if (typeof this.api.requestAccess === "function") {
        keyResult = await this.api.requestAccess();
      } else if (typeof this.api.getPublicKey === "function") {
        keyResult = await this.api.getPublicKey();
      } else {
        throw new Error(
          "FreighterAdapter: Freighter API does not export requestAccess or getPublicKey."
        );
      }

      if (typeof keyResult === "string" && keyResult.trim()) {
        return keyResult.trim();
      }

      if (typeof keyResult === "object" && keyResult !== null) {
        const resObj = keyResult as { address?: string; error?: string };
        if (resObj.error) {
          throw new Error(`FreighterAdapter: Connection error — ${resObj.error}`);
        }
        if (resObj.address && typeof resObj.address === "string" && resObj.address.trim()) {
          return resObj.address.trim();
        }
      }

      throw new Error("FreighterAdapter: Failed to retrieve valid public key from Freighter.");
    } catch (error) {
      if ((error as Error).message.startsWith("FreighterAdapter:")) {
        throw error;
      }
      throw new Error(`FreighterAdapter: Connection failed — ${(error as Error).message}`);
    }
  }

  /**
   * Prompts Freighter to sign an XDR transaction envelope.
   *
   * @param xdr - Base64 XDR string of the transaction
   * @param opts - Signing options including networkPassphrase
   * @returns The signed transaction base64 XDR string
   * @throws `Error` if Freighter is not installed, user rejects, or signing fails.
   */
  async signTransaction(
    xdr: string,
    opts?: SignTransactionOptions
  ): Promise<string> {
    if (!xdr?.trim()) {
      throw new Error("FreighterAdapter: `xdr` must be a non-empty string.");
    }

    if (!this.isAvailable()) {
      throw new Error(
        "FreighterAdapter: Freighter wallet extension is not installed or available."
      );
    }

    if (typeof this.api.signTransaction !== "function") {
      throw new Error(
        "FreighterAdapter: Freighter API does not export `signTransaction` method."
      );
    }

    try {
      const signResult = await this.api.signTransaction(xdr.trim(), {
        networkPassphrase: opts?.networkPassphrase,
        network: opts?.network,
        accountToSign: opts?.accountToSign,
      });

      if (typeof signResult === "string" && signResult.trim()) {
        return signResult.trim();
      }

      if (typeof signResult === "object" && signResult !== null) {
        const resObj = signResult as { signedTxXdr?: string; error?: string };
        if (resObj.error) {
          throw new Error(`FreighterAdapter: Signing rejected or failed — ${resObj.error}`);
        }
        if (resObj.signedTxXdr && typeof resObj.signedTxXdr === "string" && resObj.signedTxXdr.trim()) {
          return resObj.signedTxXdr.trim();
        }
      }

      throw new Error("FreighterAdapter: Freighter returned an invalid or empty signature response.");
    } catch (error) {
      if ((error as Error).message.startsWith("FreighterAdapter:")) {
        throw error;
      }
      throw new Error(`FreighterAdapter: Transaction signing failed — ${(error as Error).message}`);
    }
  }
}
