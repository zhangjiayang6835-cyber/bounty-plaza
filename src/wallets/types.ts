export interface WalletAdapter {
  readonly name: string;
  isAvailable(): boolean;
  connect(): Promise<string>;
  signTransaction(xdr: string, opts?: { networkPassphrase?: string }): Promise<string>;
}
