import type { WalletAdapter } from "./types";

export class FreighterAdapter implements WalletAdapter {
  readonly name = "Freighter";

  isAvailable(): boolean {
    return typeof (globalThis as Record<string, unknown>)["freighterAPI"] !== "undefined";
  }

  async connect(): Promise<string> {
    if (!this.isAvailable()) {
      throw new Error(
        "Freighter wallet extension is not installed. Please install it from https://freighter.app"
      );
    }

    const { getPublicAddress } = await import("@stellar/freighter-api");
    try {
      const address = await getPublicAddress();
      return address;
    } catch (err) {
      throw new Error(
        `Failed to connect to Freighter wallet: ${err instanceof Error ? err.message : String(err)}`
      );
    }
  }

  async signTransaction(
    xdr: string,
    opts?: { networkPassphrase?: string }
  ): Promise<string> {
    if (!this.isAvailable()) {
      throw new Error(
        "Freighter wallet extension is not installed. Please install it from https://freighter.app"
      );
    }

    const { signTransaction } = await import("@stellar/freighter-api");
    try {
      const signedXDR = await signTransaction(xdr, {
        networkPassphrase: opts?.networkPassphrase,
      });
      return signedXDR;
    } catch (err) {
      throw new Error(
        `Failed to sign transaction with Freighter: ${err instanceof Error ? err.message : String(err)}`
      );
    }
  }
}
