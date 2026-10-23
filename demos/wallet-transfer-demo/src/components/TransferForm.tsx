import { useEffect } from "react";
import type { ChainId, TransferSpeed } from "@asctp/parabola";
import type { useArcWallet } from "../hooks/useArcWallet.js";
import type { useStellarWallet } from "../hooks/useStellarWallet.js";

export interface TransferFormState {
  from: ChainId;
  to: ChainId;
  amount: string;
  recipient: string;
  speed: TransferSpeed;
  /** Whether to attach options.destinationSigner (single-call path) or leave the transfer
   *  "pending" and complete it separately (two-step path); both are real Parabola patterns. */
  useDestinationSigner: boolean;
  /** Let the Onderhaus paymaster complete the mint and pay the destination fee, so no
   *  destination wallet is needed. Overrides useDestinationSigner while on. */
  sponsored: boolean;
}

const ARC_RECIPIENT_PATTERN = /^0x[a-fA-F0-9]{40}$/;
const STELLAR_RECIPIENT_PATTERN = /^[GC][A-Z2-7]{55}$/;

const TOGGLE_INFO =
  "When turned on, both wallets must be connected. When turned off, only the source wallet is needed. You must provide a recipient address, and manually finish the mint.";

const SPONSOR_INFO =
  "Burn from the source wallet, then let the Onderhaus paymaster submit the mint and pay the destination fee. No destination wallet is needed. You just provide the recipient address.";

export function recipientError(to: ChainId, recipient: string): string | null {
  if (!recipient) return null;
  const pattern = to === "arc" ? ARC_RECIPIENT_PATTERN : STELLAR_RECIPIENT_PATTERN;
  if (pattern.test(recipient)) return null;
  return to === "arc" ? "Expected a 0x-prefixed EVM address" : "Expected a Stellar G... or C... address";
}

interface Props {
  value: TransferFormState;
  onChange: (next: TransferFormState) => void;
  arcWallet: ReturnType<typeof useArcWallet>;
  stellarWallet: ReturnType<typeof useStellarWallet>;
  onSubmit: () => void;
  submitting: boolean;
  sponsorAvailable: boolean;
}

export function TransferForm({ value, onChange, arcWallet, stellarWallet, onSubmit, submitting, sponsorAvailable }: Props) {
  const sourceWallet = value.from === "arc" ? arcWallet : stellarWallet;
  const destinationWallet = value.to === "arc" ? arcWallet : stellarWallet;

  const sourceReady = sourceWallet.status === "connected";
  // When sponsored, Onderhaus completes the mint, so no destination wallet is needed. Otherwise
  // the destination wallet is only needed for the single-call (destinationSigner) path.
  const destinationReady =
    value.sponsored || !value.useDestinationSigner || destinationWallet.status === "connected";
  // The recipient address is typed in whenever this app is not pulling it from a connected
  // destination wallet, i.e. the two-step path and the sponsored path.
  const needsRecipient = value.sponsored || !value.useDestinationSigner;
  const recipientErr = needsRecipient ? recipientError(value.to, value.recipient) : null;
  const canSubmit = sourceReady && destinationReady && !recipientErr && Number(value.amount) > 0 && !submitting;

  // Most demo transfers are to yourself, across your own two wallets. Default the
  // recipient to the destination wallet's own address as soon as it connects, rather
  // than making the user retype an address the app already has. Only fills an empty
  // field, so it never clobbers a recipient someone typed in to pay out to a third party.
  useEffect(() => {
    if (destinationWallet.status === "connected" && destinationWallet.address && !value.recipient) {
      onChange({ ...value, recipient: destinationWallet.address });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [destinationWallet.status, destinationWallet.address, value.to]);

  function flipDirection() {
    onChange({ ...value, from: value.to, to: value.from, recipient: "" });
  }

  function useConnectedAddress() {
    if (destinationWallet.address) {
      onChange({ ...value, recipient: destinationWallet.address });
    }
  }


  return (
    <form
      className="transfer-form"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
    >
      <div className="direction-row">
        <span className="direction-chain">{value.from === "arc" ? "Arc" : "Stellar"}</span>
        <button type="button" className="link-button" onClick={flipDirection} aria-label="Flip direction">
          &rarr;
        </button>
        <span className="direction-chain">{value.to === "arc" ? "Arc" : "Stellar"}</span>
      </div>

      <label>
        Amount (USDC)
        <input
          type="text"
          inputMode="decimal"
          placeholder="10.00"
          value={value.amount}
          onChange={(e) => onChange({ ...value, amount: e.target.value })}
        />
      </label>

      <label>
        Speed
        <select
          value={value.speed}
          onChange={(e) => onChange({ ...value, speed: e.target.value as TransferSpeed })}
        >
          <option value="standard">Standard (no fee)</option>
          <option value="fast">Fast (small fee)</option>
        </select>
      </label>

      <div className="toggle-group">
        <label className="toggle-row">
          <span className="toggle-switch">
            <input
              type="checkbox"
              checked={value.useDestinationSigner && !value.sponsored}
              disabled={value.sponsored}
              onChange={(e) => onChange({ ...value, useDestinationSigner: e.target.checked })}
            />
            <span className="toggle-track" aria-hidden="true" />
          </span>
          Complete the mint automatically
          <span className="info-tooltip">
            <button type="button" className="info-icon" aria-label="More info">
              i
            </button>
            <span className="info-bubble" role="tooltip">
              {TOGGLE_INFO}
            </span>
          </span>
        </label>

        <label className="toggle-row">
          <span className="toggle-switch">
            <input
              type="checkbox"
              checked={value.sponsored}
              disabled={!sponsorAvailable}
              title={sponsorAvailable ? undefined : "Onderhaus is not configured or not responding"}
              onChange={(e) => onChange({ ...value, sponsored: e.target.checked })}
            />
            <span className="toggle-track" aria-hidden="true" />
          </span>
          Sponsor the mint with Onderhaus
          <span className="info-tooltip">
            <button type="button" className="info-icon" aria-label="More info">
              i
            </button>
            <span className="info-bubble" role="tooltip">
              {SPONSOR_INFO}
            </span>
          </span>
        </label>
      </div>

      {needsRecipient && (
        <label>
          <span className="label-row">
            Recipient ({value.to === "arc" ? "Arc address" : "Stellar address"})
            {destinationWallet.address && destinationWallet.address !== value.recipient && (
              <button type="button" className="link-button" onClick={useConnectedAddress}>
                Use connected address
              </button>
            )}
          </span>
          <input
            type="text"
            placeholder={value.to === "arc" ? "0x..." : "G..."}
            value={value.recipient}
            onChange={(e) => onChange({ ...value, recipient: e.target.value })}
          />
          {recipientErr && <span className="field-error">{recipientErr}</span>}
        </label>
      )}

      <button type="submit" disabled={!canSubmit}>
        {submitting ? "Submitting..." : "Transfer"}
      </button>
    </form>
  );
}
