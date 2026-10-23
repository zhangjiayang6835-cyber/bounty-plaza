import { useCallback, useEffect, useState } from "react";
import type { StellarSigner } from "@asctp/parabola";
import { connectStellarWallet, stellarWalletStillConnected } from "../lib/stellarWallet.js";
import type { WalletStatus } from "./useArcWallet.js";

export function useStellarWallet() {
  const [status, setStatus] = useState<WalletStatus>("idle");
  const [signer, setSigner] = useState<StellarSigner | null>(null);
  const [address, setAddress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const connect = useCallback(async () => {
    setStatus("connecting");
    setError(null);
    try {
      const result = await connectStellarWallet();
      setSigner(result.signer);
      setAddress(result.address);
      setStatus("connected");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  const disconnect = useCallback(() => {
    setSigner(null);
    setAddress(null);
    setStatus("idle");
    setError(null);
  }, []);

  useEffect(() => {
    if (status !== "connected" || !address) return;
    let cancelled = false;

    // Window focus fires the instant Freighter's own sign/approve popup closes, which is
    // indistinguishable at the DOM-event level from the user having disconnected the
    // wallet while the tab was in the background. A single check right at that moment can
    // catch Freighter mid-transition and read as "not connected" even though nothing is
    // actually wrong (confirmed this by watching a real sign flow trip it). Requiring a
    // second check, a beat later, to agree before disconnecting filters that out without
    // giving up on detecting a real external disconnect.
    function recheck(): void {
      if (!address) return;
      void stellarWalletStillConnected(address).then((firstCheck) => {
        if (firstCheck || cancelled) return;
        setTimeout(() => {
          if (cancelled) return;
          void stellarWalletStillConnected(address).then((secondCheck) => {
            if (!secondCheck && !cancelled) disconnect();
          });
        }, 1500);
      });
    }

    function handleVisibilityChange(): void {
      if (document.visibilityState === "visible") recheck();
    }

    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("focus", recheck);

    return () => {
      cancelled = true;
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("focus", recheck);
    };
  }, [status, address, disconnect]);

  return { status, signer, address, error, connect, disconnect };
}
