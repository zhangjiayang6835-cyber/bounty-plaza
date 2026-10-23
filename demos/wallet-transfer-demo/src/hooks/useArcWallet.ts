import { useCallback, useEffect, useState } from "react";
import type { Address } from "viem";
import type { ArcSigner, Network } from "@asctp/parabola";
import { connectArcWallet } from "../lib/arcWallet.js";

export type WalletStatus = "idle" | "connecting" | "connected" | "error";

export function useArcWallet(network: Network) {
  const [status, setStatus] = useState<WalletStatus>("idle");
  const [signer, setSigner] = useState<ArcSigner | null>(null);
  const [address, setAddress] = useState<Address | null>(null);
  const [error, setError] = useState<string | null>(null);

  const connect = useCallback(async () => {
    setStatus("connecting");
    setError(null);
    try {
      const result = await connectArcWallet(network);
      setSigner(result.signer);
      setAddress(result.address);
      setStatus("connected");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [network]);

  const disconnect = useCallback(() => {
    setSigner(null);
    setAddress(null);
    setStatus("idle");
    setError(null);
  }, []);

  // MetaMask (and other EIP-1193 wallets) disconnecting or switching accounts from
  // within the wallet's own UI doesn't call anything in this app. Without this
  // listener the app keeps showing "connected" to a wallet that no longer agrees.
  // accountsChanged fires with an empty array on disconnect, or a new account on switch;
  // either way the viem WalletClient built in connectArcWallet() is bound to the old
  // account, so the only correct response is to drop it and require reconnecting.
  //
  // The EIP-1193 "disconnect" event is not a reliable signal on its own: it has been
  // observed firing around a transaction's own confirmation lifecycle, not just a real
  // wallet disconnect. Confirmed via eth_accounts (a passive check, no popup) before
  // actually dropping the session, the same defensive pattern used for Freighter, which
  // hit the identical false-positive class of bug.
  useEffect(() => {
    const ethereum = window.ethereum;
    if (!ethereum?.on) return;
    let cancelled = false;

    function handleAccountsChanged(...args: unknown[]): void {
      const accounts = args[0] as string[];
      if (accounts.length === 0 || accounts[0]?.toLowerCase() !== address?.toLowerCase()) {
        disconnect();
      }
    }

    function verifyAndDisconnect(): void {
      void ethereum!
        .request({ method: "eth_accounts" })
        .then((result) => {
          const accounts = result as string[];
          if (!cancelled && accounts.length === 0) disconnect();
        })
        .catch(() => {
          // If we can't even ask, don't assume disconnected on that basis alone.
        });
    }

    ethereum.on("accountsChanged", handleAccountsChanged);
    ethereum.on("disconnect", verifyAndDisconnect);

    return () => {
      cancelled = true;
      ethereum.removeListener?.("accountsChanged", handleAccountsChanged);
      ethereum.removeListener?.("disconnect", verifyAndDisconnect);
    };
  }, [address, disconnect]);

  return { status, signer, address, error, connect, disconnect };
}
