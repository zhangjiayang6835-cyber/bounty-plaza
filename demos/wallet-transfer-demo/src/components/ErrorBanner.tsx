import { useState } from "react";
import type { ChainId, Network } from "@asctp/parabola";
import { arcNetworkConfig } from "../lib/network.js";
import type { RecoverableTransferContext } from "../hooks/useTransfer.js";

function explorerUrl(chain: ChainId, txHash: string, network: Network): string {
  if (chain === "arc") return `${arcNetworkConfig(network).explorerUrl}/tx/${txHash}`;
  const stellarNetwork = network === "mainnet" ? "public" : "testnet";
  return `https://stellar.expert/explorer/${stellarNetwork}/tx/${txHash}`;
}

interface Props {
  message: string;
  recoverableBurnTxHash: string | null;
  recoverableTransfer?: RecoverableTransferContext | null;
  submissionUncertain: boolean;
  destinationWalletConnected: boolean;
  onRecover: () => void;
  recovering: boolean;
  onDismiss: () => void;
}

/**
 * transfer() throwing does not mean nothing happened: the source-chain burn step can
 * succeed and then a later step (attestation polling, the mint call) can still fail.
 * transfer() rethrows those as a TransferError carrying burnTxHash (see src/errors.ts) --
 * recoverableBurnTxHash reflects that, and this banner turns into a recovery panel that
 * finishes the same burn with completeMint() instead of inviting a second burn. Separately,
 * an approve step's own confirmation can time out before the burn is ever attempted
 * (submissionUncertain): there's no burn hash to recover with, but that transaction was
 * still genuinely broadcast, so this banner never claims "nothing happened" for that case
 * either.
 */
export function ErrorBanner({
  message,
  recoverableBurnTxHash,
  recoverableTransfer,
  submissionUncertain,
  destinationWalletConnected,
  onRecover,
  recovering,
  onDismiss,
}: Props) {
  const [copied, setCopied] = useState(false);

  async function handleCopyBurnHash() {
    if (!recoverableBurnTxHash) return;
    try {
      await navigator.clipboard.writeText(recoverableBurnTxHash);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="error-banner" role="alert">
      <p>{message}</p>
      {recoverableBurnTxHash ? (
        <div>
          <p>
            The source-chain burn already succeeded and funds left{" "}
            {recoverableTransfer ? recoverableTransfer.from : "the source chain"} safely (tx{" "}
            <code>{recoverableBurnTxHash}</code>
            {recoverableTransfer && (
              <>
                {" "}
                &middot;{" "}
                <a
                  href={explorerUrl(
                    recoverableTransfer.from,
                    recoverableBurnTxHash,
                    recoverableTransfer.network,
                  )}
                  target="_blank"
                  rel="noreferrer"
                >
                  View on explorer
                </a>
              </>
            )}
            ); the funds haven't minted on{" "}
            {recoverableTransfer ? recoverableTransfer.to : "the destination chain"} yet.{" "}
            {destinationWalletConnected
              ? "Complete the transfer below rather than re-submitting from scratch (which would burn a second time)."
              : `Connect the ${recoverableTransfer ? recoverableTransfer.to : "destination"} wallet, then complete the transfer below rather than re-submitting from scratch.`}
          </p>
        </div>
      ) : submissionUncertain ? (
        <p>
          A transaction was broadcast (likely the token approval) but its confirmation timed
          out before the burn was attempted, so no funds have left the source chain. It may
          still land on its own; check your address on the source-chain explorer if you want
          to confirm before retrying, though retrying is low-risk here since approvals just
          overwrite the allowance rather than accumulate.
        </p>
      ) : (
        <p>Nothing was submitted on-chain yet, so it's safe to retry.</p>
      )}
      <div className="error-banner-actions">
        {recoverableBurnTxHash && (
          <>
            <button onClick={onRecover} disabled={!destinationWalletConnected || recovering}>
              {recovering ? "Completing transfer..." : "Complete transfer"}
            </button>
            <button className="secondary" type="button" onClick={handleCopyBurnHash}>
              {copied ? "Copied burn hash" : "Copy burn hash"}
            </button>
          </>
        )}
        <button className="link-button" onClick={onDismiss}>
          Dismiss
        </button>
      </div>
    </div>
  );
}
