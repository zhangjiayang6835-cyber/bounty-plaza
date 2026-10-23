import { useCallback, useState } from "react";
import {
  transfer,
  estimateFee,
  completeMint,
  TransferError,
  SubmissionTimeoutError,
  type ChainId,
  type Network,
  type TransferParams,
  type TransferResult,
  type EstimateFeeParams,
  type FeeEstimate,
  type CompleteMintParams,
} from "@asctp/parabola";

export type TransferUiStatus = "idle" | "submitting" | "success" | "pending" | "error";

export interface RecoverableTransferContext {
  burnTxHash: string;
  attestationHash?: string;
  from: ChainId;
  to: ChainId;
  network: Network;
  recipient: string;
}

export function useTransfer() {
  const [status, setStatus] = useState<TransferUiStatus>("idle");
  const [result, setResult] = useState<TransferResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Set whenever transfer() throws a TransferError with a non-empty burnTxHash: the burn
  // succeeded on the source chain, so the UI can recover via completeMint() using the
  // captured direction and network from the original submit call even if the form changed.
  const [recoverableBurnTxHash, setRecoverableBurnTxHash] = useState<string | null>(null);
  const [recoverableTransfer, setRecoverableTransfer] = useState<RecoverableTransferContext | null>(
    null,
  );
  // Set for a SubmissionTimeoutError that isn't a TransferError, i.e. an approve step's
  // confirmation timed out, not the burn itself. There's no burn hash to recover with here
  // (the burn was never reached), but it's still wrong to claim nothing was submitted: this
  // specific transaction was broadcast, its outcome is just unconfirmed.
  const [submissionUncertain, setSubmissionUncertain] = useState(false);

  const [feeEstimate, setFeeEstimate] = useState<FeeEstimate | null>(null);
  const [estimating, setEstimating] = useState(false);

  const submit = useCallback(async (params: TransferParams): Promise<TransferResult | null> => {
    const capturedDirection = {
      from: params.from,
      to: params.to,
      network: params.network ?? "mainnet",
      recipient: params.recipient,
    };
    setStatus("submitting");
    setError(null);
    setRecoverableBurnTxHash(null);
    setRecoverableTransfer(null);
    setSubmissionUncertain(false);
    try {
      const transferResult = await transfer(params);
      setResult(transferResult);
      setRecoverableTransfer({
        ...capturedDirection,
        burnTxHash: transferResult.burnTxHash,
        attestationHash: transferResult.attestationHash || undefined,
      });
      setStatus(transferResult.status === "success" ? "success" : "pending");
      return transferResult;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
      if (err instanceof TransferError && err.burnTxHash.trim().length > 0) {
        setRecoverableBurnTxHash(err.burnTxHash);
        setRecoverableTransfer({
          ...capturedDirection,
          burnTxHash: err.burnTxHash,
          attestationHash: err.attestationHash,
        });
      } else if (err instanceof SubmissionTimeoutError) {
        setSubmissionUncertain(true);
      }
      setStatus("error");
      return null;
    }
  }, []);

  const finishPending = useCallback(async (params: CompleteMintParams) => {
    setStatus("submitting");
    setError(null);
    try {
      const completeResult = await completeMint(params);
      setResult((previous) =>
        previous
          ? {
              ...previous,
              status: "success",
              mintTxHash: completeResult.mintTxHash,
              attestationHash: completeResult.attestationHash,
            }
          : {
              status: "success",
              transferMode: "standard",
              burnTxHash: params.burnTxHash,
              mintTxHash: completeResult.mintTxHash,
              attestationHash: completeResult.attestationHash,
              fee: "0",
              durationMs: 0,
            },
      );
      setRecoverableBurnTxHash(null);
      setStatus("success");
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
      if (err instanceof TransferError && err.burnTxHash.trim().length > 0) {
        setRecoverableBurnTxHash(err.burnTxHash);
      } else if (err instanceof SubmissionTimeoutError) {
        setSubmissionUncertain(true);
      }
      setStatus("error");
    }
  }, []);

  // Marks the pending transfer complete from a mint produced outside this hook, i.e. by the
  // Onderhaus sponsor rather than by completeMint() with a local wallet. The burn and
  // attestation already happened, so only the final hashes and status change.
  const markCompleted = useCallback((mintTxHash: string, attestationHash: string) => {
    setResult((previous) =>
      previous
        ? {
            ...previous,
            status: "success",
            mintTxHash,
            attestationHash: attestationHash || previous.attestationHash,
          }
        : previous,
    );
    setRecoverableBurnTxHash(null);
    setStatus("success");
  }, []);

  const estimate = useCallback(async (params: EstimateFeeParams) => {
    setEstimating(true);
    try {
      setFeeEstimate(await estimateFee(params));
    } catch {
      setFeeEstimate(null);
    } finally {
      setEstimating(false);
    }
  }, []);

  const reset = useCallback(() => {
    setStatus("idle");
    setResult(null);
    setError(null);
    setRecoverableBurnTxHash(null);
    setRecoverableTransfer(null);
    setSubmissionUncertain(false);
  }, []);

  return {
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
  };
}
