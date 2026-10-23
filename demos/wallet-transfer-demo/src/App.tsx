import { useEffect, useState } from "react";
import type { ChainId, TransferParams, CompleteMintParams, Network } from "@asctp/parabola";
import { DEFAULT_NETWORK } from "./lib/network.js";
import { completeSponsored, pingReadyz, sponsorConfigured } from "./lib/onderhaus.js";
import { useArcWallet } from "./hooks/useArcWallet.js";
import { useStellarWallet } from "./hooks/useStellarWallet.js";
import { useTransfer } from "./hooks/useTransfer.js";
import { NetworkSelector } from "./components/NetworkSelector.js";
import { ArcWalletConnect } from "./components/ArcWalletConnect.js";
import { StellarWalletConnect } from "./components/StellarWalletConnect.js";
import { TransferForm, type TransferFormState } from "./components/TransferForm.js";
import { FeeEstimate } from "./components/FeeEstimate.js";
import { TransferStatus } from "./components/TransferStatus.js";
import { ErrorBanner } from "./components/ErrorBanner.js";

const initialForm: TransferFormState = {
  from: "arc",
  to: "stellar",
  amount: "",
  recipient: "",
  speed: "standard",
  useDestinationSigner: true,
  sponsored: false,
};

export function App() {
  const [network, setNetwork] = useState<Network>(DEFAULT_NETWORK);
  const arcWallet = useArcWallet(network);
  const stellarWallet = useStellarWallet();
  const {
    status,
    result,
    error,
    recoverableBurnTxHash,
    recoverableTransfer,
    submissionUncertain,
    submit,
    finishPending,
    markCompleted,
    feeEstimate,
    estimating,
    estimate,
    reset,
  } = useTransfer();

  const [form, setForm] = useState<TransferFormState>(initialForm);
  const [sponsoring, setSponsoring] = useState(false);
  const [sponsorError, setSponsorError] = useState<string | null>(null);
  // The sponsor toggle is available only when Onderhaus is configured and its /readyz probe
  // answers ok, so the user cannot pick a path that would fail at submission.
  const [sponsorReady, setSponsorReady] = useState(false);

  useEffect(() => {
    if (!sponsorConfigured) return;
    let active = true;
    pingReadyz().then((ready) => {
      if (active) setSponsorReady(ready);
    });
    return () => {
      active = false;
    };
  }, []);

  const sponsorAvailable = sponsorConfigured && sponsorReady;

  // An Arc signer is a viem WalletClient bound to one chain, so switching networks while a
  // wallet is connected would leave a signer pointed at the wrong chain. Drop both and clear
  // any in-flight result so the user reconnects on the network they just chose.
  function handleNetworkChange(next: Network) {
    if (next === network) return;
    arcWallet.disconnect();
    stellarWallet.disconnect();
    reset();
    setSponsorError(null);
    setNetwork(next);
  }

  // form.from and form.to are runtime values, so the direction has to be restated as a
  // literal pair for the compiler to select the signers the SDK requires: `signer` native to
  // the source chain, and options.destinationSigner native to the destination chain. The form
  // only ever holds the two supported directions, which flipDirection() preserves.
  function burnParams(): TransferParams | null {
    const shared = {
      amount: form.amount,
      recipient: form.recipient,
      speed: form.speed,
      network,
    };

    // Sponsored transfers are completed by Onderhaus, so they never carry a destinationSigner;
    // the burn goes through and leaves the transfer pending for the paymaster to finish.
    const attachDestination = form.useDestinationSigner && !form.sponsored;

    if (form.from === "arc") {
      const signer = arcWallet.signer;
      if (!signer) return null;
      const destinationSigner = attachDestination ? stellarWallet.signer : null;
      return {
        ...shared,
        from: "arc",
        to: "stellar",
        signer,
        options: destinationSigner ? { destinationSigner } : undefined,
      };
    }

    const signer = stellarWallet.signer;
    if (!signer) return null;
    const destinationSigner = attachDestination ? arcWallet.signer : null;
    return {
      ...shared,
      from: "stellar",
      to: "arc",
      signer,
      options: destinationSigner ? { destinationSigner } : undefined,
    };
  }

  // Builds CompleteMintParams using the stored direction and network from the original burn
  // when available, so flipping the form direction after a burn does not pass the wrong
  // source/destination pair to completeMint().
  function mintParams(
    burnTxHash: string,
    targetTo: ChainId = recoverableTransfer?.to ?? form.to,
    targetNetwork: Network = recoverableTransfer?.network ?? network,
  ): CompleteMintParams | null {
    if (targetTo === "arc") {
      const signer = arcWallet.signer;
      return signer ? { from: "stellar", to: "arc", burnTxHash, signer, network: targetNetwork } : null;
    }
    const signer = stellarWallet.signer;
    return signer ? { from: "arc", to: "stellar", burnTxHash, signer, network: targetNetwork } : null;
  }

  // The mint runs on the destination chain of the pending/recoverable transfer (or form.to when idle).
  function destinationWalletConnected(targetTo: ChainId = recoverableTransfer?.to ?? form.to): boolean {
    return targetTo === "arc" ? arcWallet.signer !== null : stellarWallet.signer !== null;
  }

  async function handleSubmit() {
    const params = burnParams();
    if (!params) return;

    setSponsorError(null);
    const transferResult = await submit(params);
    // In sponsored mode the burn returns pending; hand it straight to Onderhaus to finish,
    // so the user never sees a manual completion step.
    if (form.sponsored && transferResult?.status === "pending") {
      await sponsorComplete(transferResult.burnTxHash);
    }
  }

  async function handleCompleteMint() {
    if (!result) return;
    const params = mintParams(result.burnTxHash);
    if (!params) return;

    await finishPending(params);
  }

  async function handleRecoverMint() {
    if (!recoverableBurnTxHash) return;
    const params = mintParams(
      recoverableBurnTxHash,
      recoverableTransfer?.to ?? form.to,
      recoverableTransfer?.network ?? network,
    );
    if (!params) return;

    await finishPending(params);
  }

  // Onderhaus completes the mint from its own funded account, so the sponsored path needs no
  // destination wallet, only the burn hash and the recipient the burn already committed to.
  async function sponsorComplete(burnTxHash: string) {
    const activeFrom = recoverableTransfer?.from ?? form.from;
    const activeTo = recoverableTransfer?.to ?? form.to;
    const activeRecipient = recoverableTransfer?.recipient ?? form.recipient;
    const activeNetwork = recoverableTransfer?.network ?? network;
    setSponsoring(true);
    setSponsorError(null);
    try {
      const sponsored = await completeSponsored({
        burnTxHash,
        from: activeFrom,
        to: activeTo,
        recipient: activeRecipient,
        network: activeNetwork,
      });
      markCompleted(sponsored.mintTxHash, sponsored.attestationHash);
    } catch (err) {
      setSponsorError(err instanceof Error ? err.message : String(err));
    } finally {
      setSponsoring(false);
    }
  }

  function handleCompleteSponsored() {
    if (!result) return;
    void sponsorComplete(result.burnTxHash);
  }

  const activeFrom = recoverableTransfer?.from ?? form.from;
  const activeTo = recoverableTransfer?.to ?? form.to;
  const activeNetwork = recoverableTransfer?.network ?? network;

  return (
    <div className="app">
      <header>
        <div className="header-row">
          <h1>Parabola wallet transfer demo</h1>
          <NetworkSelector
            network={network}
            onChange={handleNetworkChange}
            disabled={status === "submitting"}
          />
        </div>
        <p className="subtitle">
          Connect your own wallets and trigger a real, non-custodial USDC transfer between Arc
          and Stellar. See{" "}
          <a href="https://github.com/ASCTP/parabola/blob/main/INTEGRATION.md" target="_blank" rel="noreferrer">
            INTEGRATION.md
          </a>{" "}
          for the patterns this app illustrates.
        </p>
      </header>

      <section className="wallets">
        <ArcWalletConnect wallet={arcWallet} />
        <StellarWalletConnect wallet={stellarWallet} />
      </section>

      <section>
        <TransferForm
          value={form}
          onChange={setForm}
          arcWallet={arcWallet}
          stellarWallet={stellarWallet}
          onSubmit={handleSubmit}
          submitting={status === "submitting" || sponsoring}
          sponsorAvailable={sponsorAvailable}
        />
        <FeeEstimate
          from={form.from}
          to={form.to}
          amount={form.amount}
          speed={form.speed}
          network={network}
          feeEstimate={feeEstimate}
          estimating={estimating}
          onEstimate={estimate}
        />
      </section>

      {error && (
        <ErrorBanner
          message={error}
          recoverableBurnTxHash={recoverableBurnTxHash}
          recoverableTransfer={recoverableTransfer}
          submissionUncertain={submissionUncertain}
          destinationWalletConnected={destinationWalletConnected(activeTo)}
          onRecover={handleRecoverMint}
          recovering={status === "submitting"}
          onDismiss={reset}
        />
      )}

      {result && (
        <section>
          <TransferStatus
            result={result}
            from={activeFrom}
            to={activeTo}
            network={activeNetwork}
            onCompleteMint={handleCompleteMint}
            completing={status === "submitting"}
            destinationWalletConnected={destinationWalletConnected(activeTo)}
            onCompleteSponsored={handleCompleteSponsored}
            sponsorConfigured={sponsorAvailable}
            sponsoring={sponsoring}
            sponsorError={sponsorError}
          />
        </section>
      )}
    </div>
  );
}
