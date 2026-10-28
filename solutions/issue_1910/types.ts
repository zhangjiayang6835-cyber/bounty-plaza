/**
 * Discriminated union for transfer lifecycle progress events.
 * Upstream Reference: Parabola-org/parabola (src/types.ts)
 * Resolves Issue #1910 (and Parabola-org/parabola#6).
 */

export type TransferProgressEvent =
  | { stage: "recipient-check"; timestamp: number }
  | { stage: "approve"; timestamp: number }
  | { stage: "burn-submitted"; timestamp: number }
  | { stage: "burn-confirmed"; burnTxHash: string; timestamp: number }
  | { stage: "attestation"; burnTxHash: string; attestationHash?: string; timestamp: number }
  | { stage: "mint-submitted"; burnTxHash: string; timestamp: number }
  | { stage: "mint-confirmed"; burnTxHash: string; mintTxHash: string; timestamp: number };

export interface TransferOptionsBase {
  /** Optional progress callback invoked at transfer stage boundaries. */
  onProgress?: (event: TransferProgressEvent) => void;
  /** Max USDC fee tolerated for a fast transfer. */
  maxFee?: string;
  /** Max seconds to wait before falling back to standard transfer. */
  maxWait?: number;
}
