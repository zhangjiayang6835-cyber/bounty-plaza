import type { SignTransactionOptions, WalletAdapter } from "./types";

const NOT_INSTALLED =
  "Freighter wallet extension is not installed. Install it from https://freighter.app";

interface FreighterApi {
  isConnected(): Promise<boolean>;
  getPublicKey(): Promise<string>;
  signTransaction(xdr: string, opts?: { networkPassphrase?: string }): Promise<string>;
}

function getFreighter(): FreighterApi | undefined {
  const w = globalThis as unknown as { freighter?: FreighterApi };
  return w.freighter;
}

export class FreighterAdapter implements WalletAdapter {
  readonly name = "Freighter";

  isAvailable(): boolean {
    return getFreighter() !== undefined;
  }

  async connect(): Promise<string> {
    const api = getFreighter();
    if (!api) throw new Error(NOT_INSTALLED);
    const connected = await api.isConnected();
    if (!connected) throw new Error(NOT_INSTALLED);
    const publicKey = await api.getPublicKey();
    if (!publicKey) throw new Error("Freighter is locked or no account is selected.");
    return publicKey;
  }

  async signTransaction(
    xdr: string,
    opts?: SignTransactionOptions
  ): Promise<string> {
    const api = getFreighter();
    if (!api) throw new Error(NOT_INSTALLED);
    return api.signTransaction(xdr, {
      networkPassphrase: opts?.networkPassphrase,
    });
  }
}
