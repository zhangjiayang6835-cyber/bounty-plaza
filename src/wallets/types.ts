export interface SignTransactionOptions {
  networkPassphrase?: string;
  accountToSign?: string;
}

export interface WalletAdapter {
  readonly name: string;
  isAvailable(): boolean;
  connect(): Promise<string>;
  signTransaction(xdr: string, opts?: SignTransactionOptions): Promise<string>;
}

export class WalletNotInstalledError extends Error {
  constructor(walletName: string) {
    super(`${walletName} wallet extension is not installed or unavailable in the current window context.`);
    this.name = "WalletNotInstalledError";
  }
}

export class WalletConnectionError extends Error {
  constructor(walletName: string, reason: string) {
    super(`Failed to connect to ${walletName}: ${reason}`);
    this.name = "WalletConnectionError";
  }
}

export class WalletSigningError extends Error {
  constructor(walletName: string, reason: string) {
    super(`Failed to sign transaction with ${walletName}: ${reason}`);
    this.name = "WalletSigningError";
  }
}
