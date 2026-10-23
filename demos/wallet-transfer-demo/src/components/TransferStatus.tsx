import type { ChainId, Network, TransferResult } from "@asctp/parabola";
import { explorerUrl } from "../lib/explorer.js";
import { shortenTxHash, formatDurationMs } from "../lib/formatting.js";

interface Props {
  result: TransferResult;
  from: ChainId;
  to: ChainId;
  network: Network;
  onCompleteMint: () => void;
  completing: boolean;
  destinationWalletConnected: boolean;
  onCompleteSponsored: () => void;
  sponsorConfigured: boolean;
  sponsoring: boolean;
  sponsorError: string | null;
}

export function TransferStatus({
  result,
  from,
  to,
  network,
  onCompleteMint,
  completing,
  destinationWalletConnected,
  onCompleteSponsored,
  sponsorConfigured,
  sponsoring,
  sponsorError,
}: Props) {
  return (
    <div className="transfer-status">
      <ol className="status-steps">
        <li className="status-step done">
          Burn on {from}
          {": "}
          <a href={explorerUrl(from, result.burnTxHash, network)} target="_blank" rel="noreferrer">
            {shortenTxHash(result.burnTxHash)}
          </a>
        </li>
        <li className={`status-step ${result.attestationHash ? "done" : "pending"}`}>
          Attestation{result.attestationHash ? `: ${shortenTxHash(result.attestationHash)}` : "..."}
        </li>
        <li className={`status-step ${result.status === "success" ? "done" : "pending"}`}>
          {result.status === "success" ? (
            <>
              Mint on {to}
              {": "}
              <a href={explorerUrl(to, result.mintTxHash, network)} target="_blank" rel="noreferrer">
                {shortenTxHash(result.mintTxHash)}
              </a>
            </>
          ) : (
            `Mint on ${to}: pending`
          )}
        </li>
      </ol>

      <p className="status-meta">
        {result.transferMode} transfer &middot; fee {result.fee} USDC &middot; {formatDurationMs(result.durationMs)}
      </p>

      {result.status === "pending" && (
        <div className="complete-mint">
          <p className="hint">
            No destination signer was attached, so the transfer stopped after the burn and
            attestation. Finish it with the destination wallet, or let Onderhaus sponsor it and
            pay the fee for you.
          </p>
          <div className="complete-options">
            <button onClick={onCompleteMint} disabled={completing || sponsoring || !destinationWalletConnected}>
              {completing
                ? "Completing..."
                : destinationWalletConnected
                  ? "Complete with wallet"
                  : `Connect ${to} wallet to complete`}
            </button>
            {sponsorConfigured && (
              <button className="secondary" onClick={onCompleteSponsored} disabled={sponsoring || completing}>
                {sponsoring ? "Sponsoring..." : "Complete sponsored (Onderhaus)"}
              </button>
            )}
          </div>
          {sponsorError && <span className="field-error">{sponsorError}</span>}
        </div>
      )}
    </div>
  );
}
