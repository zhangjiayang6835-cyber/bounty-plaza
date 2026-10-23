import type { useStellarWallet } from "../hooks/useStellarWallet.js";
import { shortenAddress } from "../lib/formatting.js";

export function StellarWalletConnect({ wallet }: { wallet: ReturnType<typeof useStellarWallet> }) {
  return (
    <div className="wallet-card">
      <div className="wallet-card-header">
        <span className="wallet-chip">Stellar</span>
        {wallet.status === "connected" && wallet.address && (
          <code className="wallet-address">{shortenAddress(wallet.address)}</code>
        )}
      </div>
      {wallet.status !== "connected" && (
        <button onClick={wallet.connect} disabled={wallet.status === "connecting"}>
          {wallet.status === "connecting" ? "Connecting..." : "Connect Freighter"}
        </button>
      )}
      {wallet.status === "connected" && (
        <button className="link-button" onClick={wallet.disconnect}>
          Disconnect
        </button>
      )}
      {wallet.error && <p className="field-error">{wallet.error}</p>}
    </div>
  );
}
