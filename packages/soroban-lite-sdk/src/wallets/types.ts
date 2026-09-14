/**
 * soroban-lite-sdk — src/wallets/types.ts
 *
 * Common interfaces and types for Soroban wallet adapters.
 *
 * @packageDocumentation
 */

/**
 * Configuration options passed to a wallet when requesting a transaction signature.
 */
export interface SignTransactionOptions {
  /**
   * The network passphrase to validate and sign against.
   * e.g., "Test SDF Network ; September 2015" or "Public Global Stellar Network ; September 2015"
   */
  networkPassphrase?: string;

  /**
   * Optional named network identifier or alias (e.g. "TESTNET", "PUBLIC").
   */
  network?: string;

  /**
   * Optional specific public key to sign with when the wallet holds multiple accounts.
   */
  accountToSign?: string;

  /**
   * Additional implementation-specific options.
   */
  [key: string]: unknown;
}

/**
 * Common abstraction interface for browser and software wallet adapters.
 *
 * Implementations of this interface wrap vendor SDKs (e.g. Freighter, Stellar Wallets Kit)
 * providing a consistent signature and connection API for `SorobanClient.signAndSubmit`.
 */
export interface WalletAdapter {
  /**
   * Human-readable identifier for the wallet (e.g. "Freighter", "StellarWalletsKit").
   */
  readonly name: string;

  /**
   * Checks whether the underlying wallet extension or provider is installed and available
   * in the current execution environment.
   *
   * This method must be synchronous, idempotent, and must NOT trigger any modal or user prompt.
   *
   * @returns `true` if the wallet extension/provider is detected; `false` otherwise.
   */
  isAvailable(): boolean;

  /**
   * Connects to the wallet provider, requesting account access permissions from the user.
   *
   * @returns A promise resolving to the user's active Stellar public key (`G...` address).
   * @throws An `Error` if the wallet is not available, the user rejects the connection,
   *         or account retrieval fails.
   */
  connect(): Promise<string>;

  /**
   * Requests the wallet to sign an XDR-encoded Stellar transaction envelope.
   *
   * @param xdr - Base64-encoded Stellar transaction or fee-bump transaction XDR string.
   * @param opts - Optional signing parameters including network passphrase.
   * @returns A promise resolving to the signed transaction XDR string.
   * @throws An `Error` if the wallet is not available, user rejects the signature,
   *         or signing fails.
   */
  signTransaction(
    xdr: string,
    opts?: SignTransactionOptions
  ): Promise<string>;
}
