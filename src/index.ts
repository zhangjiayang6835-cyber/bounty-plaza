import { FreighterAdapter, StellarKitAdapter } from "./wallets";
import type { WalletAdapter } from "./wallets";

export { WalletAdapter, FreighterAdapter, StellarKitAdapter };

export class SorobanClient {
  private rpcUrl: string;
  private networkPassphrase: string;

  constructor(opts: { rpcUrl: string; networkPassphrase?: string } = { rpcUrl: "https://soroban-testnet.stellar.org" }) {
    this.rpcUrl = opts.rpcUrl;
    this.networkPassphrase = opts.networkPassphrase || "Test SDF Network ; September 2015";
  }

  async simulate(transactionXDR: string): Promise<string> {
    const response = await fetch(this.rpcUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "simulateTransaction", params: { transaction: transactionXDR } }),
    });
    const data = await response.json();
    if (data.error) throw new Error(data.error.message || "Simulation failed");
    return data.result as string;
  }

  async submit(transactionXDR: string): Promise<string> {
    const response = await fetch(this.rpcUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "sendTransaction", params: { transaction: transactionXDR } }),
    });
    const data = await response.json();
    if (data.error) throw new Error(data.error.message || "Submit failed");
    return data.result as string;
  }

  async signAndSubmit(
    transactionXDR: string,
    wallet: WalletAdapter,
    opts?: { networkPassphrase?: string }
  ): Promise<string> {
    const signedXDR = await wallet.signTransaction(transactionXDR, opts);
    return this.submit(signedXDR);
  }
}
