/**
 * Fail-safe stage emitter and transfer orchestrator.
 * Upstream Reference: Parabola-org/parabola (src/transfer.ts)
 */

import type { TransferProgressEvent, TransferOptionsBase } from "./types.js";

export function emitProgress(
  onProgress: ((event: TransferProgressEvent) => void) | undefined,
  event: TransferProgressEvent
): void {
  if (!onProgress) return;
  try {
    onProgress(event);
  } catch {
    // Deliberately swallowed to guarantee consumer callback exceptions
    // never disrupt or terminate an in-flight on-chain transfer.
  }
}

export interface TransferParams {
  from: "arc" | "stellar";
  to: "arc" | "stellar";
  amount: string;
  recipient: string;
  signer: any;
  options?: TransferOptionsBase & {
    destinationSigner?: any;
  };
}

export interface TransferResult {
  status: "success" | "pending";
  burnTxHash: string;
  mintTxHash?: string;
}

export async function transfer(
  params: TransferParams,
  deps: {
    assertRecipientReady: () => Promise<void>;
    approveUsdc: () => Promise<string>;
    burnUsdc: () => Promise<string>;
    pollAttestation: (burnHash: string) => Promise<{ attestation: string; message: string }>;
    mintTokens: () => Promise<string>;
  } = {
    assertRecipientReady: async () => {},
    approveUsdc: async () => "0xapprove",
    burnUsdc: async () => "0xburnhash",
    pollAttestation: async () => ({ attestation: "0xattest", message: "0xmsg" }),
    mintTokens: async () => "0xminthash",
  }
): Promise<TransferResult> {
  const onProgress = params.options?.onProgress;

  emitProgress(onProgress, { stage: "recipient-check", timestamp: Date.now() });
  await deps.assertRecipientReady();

  emitProgress(onProgress, { stage: "approve", timestamp: Date.now() });
  await deps.approveUsdc();

  emitProgress(onProgress, { stage: "burn-submitted", timestamp: Date.now() });
  const burnTxHash = await deps.burnUsdc();

  emitProgress(onProgress, { stage: "burn-confirmed", burnTxHash, timestamp: Date.now() });

  emitProgress(onProgress, { stage: "attestation", burnTxHash, timestamp: Date.now() });
  await deps.pollAttestation(burnTxHash);

  let status: "success" | "pending" = "pending";
  let mintTxHash: string | undefined;

  if (params.options?.destinationSigner) {
    emitProgress(onProgress, { stage: "mint-submitted", burnTxHash, timestamp: Date.now() });
    mintTxHash = await deps.mintTokens();
    emitProgress(onProgress, { stage: "mint-confirmed", burnTxHash, mintTxHash, timestamp: Date.now() });
    status = "success";
  }

  return {
    status,
    burnTxHash,
    mintTxHash,
  };
}
