import type { useArcWallet } from "../hooks/useArcWallet.js";
import { shortenAddress } from "../lib/formatting.js";

export function ArcWalletConnect({ wallet }: { wallet: ReturnType<typeof useArcWallet> }) {
  return (
    <div className="wallet-card">
      <div className="wallet-card-header">
        <span className="wallet-chip">Arc</span>
        {wallet.status === "connected" && wallet.address && (
          <code className="wallet-address">{shortenAddress(wallet.address)}</code>
        )}
      </div>
      {wallet.status !== "connected" && (
        <button onClick={wallet.connect} disabled={wallet.status === "connecting"}>
          {wallet.status === "connecting" ? "Connecting..." : "Connect MetaMask"}
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
