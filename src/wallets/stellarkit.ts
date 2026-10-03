import type { WalletAdapter } from "./types";

export class StellarKitAdapter implements WalletAdapter {
  readonly name = "StellarKit";

  isAvailable(): boolean {
    return typeof (globalThis as Record<string, unknown>)["stellarWalletsKit"] !== "undefined";
  }

  async connect(): Promise<string> {
    const { StellarWalletsKit, Networks, SEP10Challenge } = await import(
      "@creit.tech/stellar-wallets-kit"
    );

    const kit = new StellarWalletsKit({
      selectedWallet: "none",
    });

    let address: string;
    try {
      address = await kit.connect();
    } catch (err) {
      throw new Error(
        `Failed to connect to Stellar Wallets Kit: ${err instanceof Error ? err.message : String(err)}`
      );
    }

    if (!address) {
      throw new Error("Stellar Wallets Kit connection returned no address.");
    }

    return address;
  }

  async signTransaction(
    xdr: string,
    opts?: { networkPassphrase?: string }
  ): Promise<string> {
    const { StellarWalletsKit, Networks } = await import(
      "@creit.tech/stellar-wallets-kit"
    );

    const networkPassphrase = opts?.networkPassphrase ?? Networks.STANDALONE;

    const kit = new StellarWalletsKit({
      selectedWallet: "none",
    });

    try {
      const signedXDR = await kit.signTransaction(xdr, {
        networkPassphrase,
      });
      return signedXDR;
    } catch (err) {
      throw new Error(
        `Failed to sign transaction with Stellar Wallets Kit: ${err instanceof Error ? err.message : String(err)}`
      );
    }
  }
}
