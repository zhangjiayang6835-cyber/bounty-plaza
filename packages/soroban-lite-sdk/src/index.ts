/**
 * soroban-lite-sdk — src/index.ts
 *
 * A minimal, strongly-typed TypeScript client for interacting with Soroban
 * smart contracts on the Stellar network.
 *
 * @packageDocumentation
 */

import {
  rpc,
  Transaction,
  FeeBumpTransaction,
  xdr,
  Networks,
  TransactionBuilder,
  Account,
} from "@stellar/stellar-sdk";

import { WalletAdapter } from "./wallets/types";

// ─── Re-exports ───────────────────────────────────────────────────────────────

export { Networks };
export * from "./wallets";

// ─── Constants ────────────────────────────────────────────────────────────────

/** Public Stellar Soroban RPC endpoints */
export const RPC_ENDPOINTS = {
  TESTNET: "https://soroban-testnet.stellar.org",
  MAINNET: "https://mainnet.stellar.validationcloud.io/v1/",
  FUTURENET: "https://rpc-futurenet.stellar.org",
} as const;

/** Default polling configuration */
const DEFAULT_MAX_ATTEMPTS = 10;
const DEFAULT_DELAY_MS = 1_000;

// ─── Types ────────────────────────────────────────────────────────────────────

/** Supported Stellar network identifiers */
export type NetworkName = "TESTNET" | "MAINNET" | "FUTURENET";

/**
 * Configuration for constructing a SorobanClient.
 *
 * You can either provide a named `network` (which auto-resolves the RPC URL
 * and passphrase) **or** supply a custom `rpcUrl` + `networkPassphrase` pair
 * for local nodes or private networks.
 */
export type SorobanConfig =
  | {
      /** One of the built-in network presets */
      network: NetworkName;
      rpcUrl?: never;
      networkPassphrase?: never;
    }
  | {
      network?: never;
      /** Custom Soroban RPC endpoint URL */
      rpcUrl: string;
      /** Stellar network passphrase */
      networkPassphrase: string;
    };

/** Options for configuring retry behaviour in pollTransactionStatus */
export interface RetryOptions {
  /** Maximum polling attempts before giving up (default: 10) */
  maxAttempts?: number;
  /** Base delay in milliseconds between attempts (default: 1000) */
  delayMs?: number;
  /**
   * When `true`, wait time follows `delayMs * 2^attempt` (exponential backoff).
   * When `false` (default), a fixed `delayMs` is used each iteration.
   */
  exponentialBackoff?: boolean;
}

/** Structured result returned by `simulateTransaction` */
export interface SimulationResult {
  /** The raw RPC response object */
  raw: rpc.Api.SimulateTransactionResponse;
  /**
   * Decoded XDR return value from the contract, if any.
   * `undefined` when the contract returns void or the response carries no result.
   */
  returnValue: xdr.ScVal | undefined;
  /** Estimated minimum resource fee in stroops, if provided */
  minResourceFee: string | undefined;
  /** Whether the simulation succeeded (no error field present) */
  success: boolean;
}

/** Result of a full sign-simulate-submit-poll cycle */
export interface SubmitResult {
  /** Final on-chain transaction response */
  transaction: rpc.Api.GetTransactionResponse;
  /** Number of polling attempts made */
  attempts: number;
}

// ─── Utility Functions ────────────────────────────────────────────────────────

/**
 * Type-guard that narrows a `SimulateTransactionResponse` to its error variant.
 *
 * @example
 * ```ts
 * const res = await server.simulateTransaction(tx);
 * if (isSimulationError(res)) {
 *   console.error(res.error);
 * }
 * ```
 */
export function isSimulationError(
  response: rpc.Api.SimulateTransactionResponse
): response is rpc.Api.SimulateTransactionErrorResponse {
  return (
    (response as rpc.Api.SimulateTransactionErrorResponse).error !== undefined
  );
}

/**
 * Safely decodes a base-64 XDR-encoded `ScVal` string.
 * Returns `undefined` instead of throwing on null / invalid input.
 *
 * @param base64 - Base-64 string produced by `ScVal.toXDR("base64")`
 */
export function decodeScVal(base64: string | null | undefined): xdr.ScVal | undefined {
  if (!base64) return undefined;
  try {
    return xdr.ScVal.fromXDR(base64, "base64");
  } catch {
    return undefined;
  }
}

/**
 * Resolves the RPC URL and network passphrase for a named network preset.
 */
export function resolveNetworkConfig(network: NetworkName): {
  rpcUrl: string;
  networkPassphrase: string;
} {
  const passphraseMap: Record<NetworkName, string> = {
    TESTNET: Networks.TESTNET,
    MAINNET: Networks.PUBLIC,
    FUTURENET: Networks.FUTURENET,
  };
  return {
    rpcUrl: RPC_ENDPOINTS[network],
    networkPassphrase: passphraseMap[network],
  };
}

// ─── SorobanClient ────────────────────────────────────────────────────────────

/**
 * `SorobanClient` — a lightweight, strongly-typed RPC client for Soroban
 * smart contract interactions on the Stellar network.
 *
 * Supports four core operations:
 * 1. **Simulating** transactions before submission (fee estimation + return value decoding).
 * 2. **Polling** for final transaction status with linear or exponential backoff.
 * 3. **Fetching** on-chain account state for transaction building.
 * 4. **Signing and Submitting** transactions via unified `WalletAdapter` integrations.
 *
 * @example
 * ```ts
 * // Named network preset
 * const client = new SorobanClient({ network: "TESTNET" });
 *
 * // Custom RPC endpoint
 * const client = new SorobanClient({
 *   rpcUrl: "https://my-rpc.example.com",
 *   networkPassphrase: Networks.TESTNET,
 * });
 * ```
 */
export class SorobanClient {
  /** The resolved network passphrase used for transaction signing */
  readonly networkPassphrase: string;

  /** The resolved RPC endpoint URL */
  readonly rpcUrl: string;

  private readonly server: rpc.Server;

  constructor(config: SorobanConfig) {
    let resolvedUrl: string;
    let resolvedPassphrase: string;

    if (config.network) {
      const resolved = resolveNetworkConfig(config.network);
      resolvedUrl = resolved.rpcUrl;
      resolvedPassphrase = resolved.networkPassphrase;
    } else {
      if (!config.rpcUrl?.trim()) {
        throw new Error("SorobanClient: `rpcUrl` must be a non-empty string.");
      }
      if (!config.networkPassphrase?.trim()) {
        throw new Error(
          "SorobanClient: `networkPassphrase` must be a non-empty string."
        );
      }
      resolvedUrl = config.rpcUrl;
      resolvedPassphrase = config.networkPassphrase;
    }

    this.rpcUrl = resolvedUrl;
    this.networkPassphrase = resolvedPassphrase;
    this.server = new rpc.Server(resolvedUrl, {
      allowHttp: resolvedUrl.startsWith("http://"),
    });
  }

  // ── RPC Access ──────────────────────────────────────────────────────────────

  /**
   * Returns the underlying `rpc.Server` instance for advanced or direct use.
   * Prefer the higher-level methods for common operations.
   */
  get rpcServer(): rpc.Server {
    return this.server;
  }

  // ── Account ─────────────────────────────────────────────────────────────────

  /**
   * Fetches the current on-chain `Account` state for a given public key.
   * Useful when building `TransactionBuilder` instances manually.
   *
   * @param publicKey - Stellar public key (G… address)
   * @throws When the account does not exist or the RPC call fails
   */
  async getAccount(publicKey: string): Promise<Account> {
    if (!publicKey?.trim()) {
      throw new Error("getAccount: `publicKey` must be a non-empty string.");
    }
    try {
      return await this.server.getAccount(publicKey);
    } catch (error) {
      throw new Error(
        `getAccount failed for ${publicKey}: ${(error as Error).message}`
      );
    }
  }

  // ── Simulation ──────────────────────────────────────────────────────────────

  /**
   * Simulates a Soroban transaction against the network without submitting it.
   *
   * Returns a `SimulationResult` containing:
   * - The raw RPC response
   * - The decoded `ScVal` return value (if any)
   * - The estimated minimum resource fee in stroops
   *
   * @param tx - A fully-built `Transaction` or `FeeBumpTransaction` envelope
   * @throws On network failure or when the simulation response carries an error
   *
   * @example
   * ```ts
   * const result = await client.simulateTransaction(tx);
   * console.log("Fee:", result.minResourceFee);
   * console.log("Return:", result.returnValue);
   * ```
   */
  async simulateTransaction(
    tx: Transaction | FeeBumpTransaction
  ): Promise<SimulationResult> {
    let response: rpc.Api.SimulateTransactionResponse;

    try {
      response = await this.server.simulateTransaction(tx);
    } catch (error) {
      throw new Error(
        `simulateTransaction: network error — ${(error as Error).message}`
      );
    }

    if (isSimulationError(response)) {
      const errResponse = response as rpc.Api.SimulateTransactionErrorResponse;
      throw new Error(
        `simulateTransaction: contract error — ${errResponse.error}`
      );
    }

    const successResponse =
      response as rpc.Api.SimulateTransactionSuccessResponse;

    const retvalBase64 = successResponse.result?.retval
      ? successResponse.result.retval.toXDR("base64")
      : undefined;

    return {
      raw: response,
      returnValue: decodeScVal(retvalBase64),
      minResourceFee: successResponse.minResourceFee,
      success: true,
    };
  }

  // ── Transaction Polling ─────────────────────────────────────────────────────

  /**
   * Polls the Soroban RPC until the submitted transaction reaches a terminal
   * state (`SUCCESS` or `FAILED`), or until the retry budget is exhausted.
   *
   * Supports optional exponential backoff to reduce RPC pressure under load.
   *
   * @param hash    - SHA-256 hash of the submitted transaction envelope
   * @param options - Optional retry configuration
   * @returns       The final `GetTransactionResponse`
   * @throws        When the retry limit is exceeded or an RPC error occurs
   *
   * @example
   * ```ts
   * const status = await client.pollTransactionStatus(hash, {
   *   maxAttempts: 15,
   *   delayMs: 2000,
   *   exponentialBackoff: true,
   * });
   * console.log(status.status); // "SUCCESS" | "FAILED"
   * ```
   */
  async pollTransactionStatus(
    hash: string,
    options: RetryOptions = {}
  ): Promise<rpc.Api.GetTransactionResponse> {
    if (!hash?.trim()) {
      throw new Error("pollTransactionStatus: `hash` must be a non-empty string.");
    }

    const {
      maxAttempts = DEFAULT_MAX_ATTEMPTS,
      delayMs = DEFAULT_DELAY_MS,
      exponentialBackoff = false,
    } = options;

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      let response: rpc.Api.GetTransactionResponse;

      try {
        response = await this.server.getTransaction(hash);
      } catch (error) {
        throw new Error(
          `pollTransactionStatus: RPC error on attempt ${attempt + 1} — ${
            (error as Error).message
          }`
        );
      }

      if (response.status !== rpc.Api.GetTransactionStatus.NOT_FOUND) {
        return response;
      }

      const waitMs = exponentialBackoff
        ? delayMs * Math.pow(2, attempt)
        : delayMs;

      await SorobanClient.sleep(waitMs);
    }

    throw new Error(
      `pollTransactionStatus: transaction ${hash} not found after ${maxAttempts} attempt(s).`
    );
  }

  // ── Wallet Sign & Submit Helper ─────────────────────────────────────────────

  /**
   * Simulates, signs with the specified `WalletAdapter`, submits to RPC, and polls
   * the transaction until confirmation.
   *
   * Complete lifecycle:
   * 1. **Simulate**: Validates transaction with `simulateTransaction(tx)`.
   * 2. **Sign**: Passes XDR to `wallet.signTransaction(xdr, { networkPassphrase })`.
   * 3. **Submit**: Sends signed transaction via `rpcServer.sendTransaction`.
   * 4. **Poll**: Awaits final status with `pollTransactionStatus(hash, options)`.
   *
   * @param tx - `Transaction`, `FeeBumpTransaction`, or base64 XDR string
   * @param wallet - An adapter conforming to `WalletAdapter` (e.g. `FreighterAdapter`, `StellarKitAdapter`)
   * @param options - Polling retry configuration
   * @returns Final `GetTransactionResponse` from the RPC node
   * @throws If wallet is invalid, simulation fails, user rejects signature, or submission fails
   *
   * @example
   * ```ts
   * const freighter = new FreighterAdapter();
   * const receipt = await client.signAndSubmit(tx, freighter);
   * console.log("Status:", receipt.status);
   * ```
   */
  async signAndSubmit(
    tx: Transaction | FeeBumpTransaction | string,
    wallet: WalletAdapter,
    options?: RetryOptions
  ): Promise<rpc.Api.GetTransactionResponse> {
    if (!wallet || typeof wallet.signTransaction !== "function") {
      throw new Error("signAndSubmit: A valid `WalletAdapter` instance must be provided.");
    }

    let parsedTx: Transaction | FeeBumpTransaction;
    let xdrString: string;

    if (typeof tx === "string") {
      if (!tx.trim()) {
        throw new Error("signAndSubmit: `tx` XDR string must not be empty.");
      }
      xdrString = tx.trim();
      parsedTx = TransactionBuilder.fromXDR(xdrString, this.networkPassphrase);
    } else if (tx && typeof (tx as any).toXDR === "function") {
      parsedTx = tx;
      xdrString = tx.toXDR();
    } else {
      throw new Error("signAndSubmit: `tx` must be a valid Transaction, FeeBumpTransaction, or XDR string.");
    }

    // 1. Simulate transaction
    await this.simulateTransaction(parsedTx);

    // 2. Request wallet signature
    let signedXdr: string;
    try {
      signedXdr = await wallet.signTransaction(xdrString, {
        networkPassphrase: this.networkPassphrase,
      });
    } catch (error) {
      throw new Error(`signAndSubmit: Wallet signing failed — ${(error as Error).message}`);
    }

    if (!signedXdr || typeof signedXdr !== "string" || !signedXdr.trim()) {
      throw new Error("signAndSubmit: Wallet returned an empty or invalid signed XDR string.");
    }

    // 3. Parse and submit signed transaction
    let signedTx: Transaction | FeeBumpTransaction;
    try {
      signedTx = TransactionBuilder.fromXDR(signedXdr.trim(), this.networkPassphrase);
    } catch (error) {
      throw new Error(`signAndSubmit: Failed to parse signed XDR from wallet — ${(error as Error).message}`);
    }

    let submitResult: rpc.Api.SendTransactionResponse;
    try {
      submitResult = await this.server.sendTransaction(signedTx);
    } catch (error) {
      throw new Error(`signAndSubmit: RPC submission failed — ${(error as Error).message}`);
    }

    if (submitResult.status === rpc.Api.SendTransactionStatus.ERROR) {
      const errorMsg = submitResult.errorResult?.toXDR("base64") || "Transaction rejected by RPC node";
      throw new Error(`signAndSubmit: RPC sendTransaction rejected with ERROR status: ${errorMsg}`);
    }

    // 4. Poll transaction status
    return await this.pollTransactionStatus(submitResult.hash, options);
  }

  // ── Ledger Info ─────────────────────────────────────────────────────────────

  /**
   * Fetches the latest ledger number and close time from the RPC endpoint.
   * Useful for setting `timebounds` or validating network connectivity.
   */
  async getLatestLedger(): Promise<rpc.Api.GetLatestLedgerResponse> {
    try {
      return await this.server.getLatestLedger();
    } catch (error) {
      throw new Error(
        `getLatestLedger failed: ${(error as Error).message}`
      );
    }
  }

  // ── Private Helpers ─────────────────────────────────────────────────────────

  private static sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
