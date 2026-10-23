import type { ChainId } from "./types.js";

/**
 * Thrown by transfer() for any failure that happens after the source-chain burn has
 * already succeeded: attestation polling (timeout or otherwise), or the destination-chain
 * mint call. Carries burnTxHash so the caller can recover with completeMint() instead of
 * losing track of funds that already left the source chain.
 */
export class TransferError extends Error {
  readonly burnTxHash: string;
  readonly attestationHash?: string;
  readonly code?: TransferErrorCode;

  constructor(
    message: string,
    burnTxHash: string,
    attestationHash?: string,
    code?: TransferErrorCode,
  ) {
    super(message);
    this.name = "TransferError";
    this.burnTxHash = burnTxHash;
    this.attestationHash = attestationHash;
    this.code = code;
  }
}

export type TransferErrorCode = "ATTESTATION_NOT_READY" | "TRANSFER_ABORTED";

/**
 * Thrown when an on-chain transaction submission times out or exhausts polling attempts.
 * Preserves the broadcast transaction hash so callers can trace or recover funds.
 */
export class SubmissionTimeoutError extends Error {
  readonly hash: string;

  constructor(message: string, hash: string) {
    super(message);
    this.name = "SubmissionTimeoutError";
    this.hash = hash;
  }
}

/**
 * Thrown before a burn when the requested amount has more significant decimal places
 * than the destination chain's USDC representation can preserve.
 */
export class AmountPrecisionError extends Error {
  readonly amount: string;
  readonly precision: number;
  readonly supportedDecimals: number;
  readonly destination: "arc" | "stellar";

  constructor(
    amount: string,
    precision: number,
    supportedDecimals: number,
    destination: "arc" | "stellar",
  ) {
    super(
      `Amount ${amount} has ${precision} decimals, exceeding destination ${destination}'s limit of ${supportedDecimals}`,
    );
    this.name = "AmountPrecisionError";
    this.amount = amount;
    this.precision = precision;
    this.supportedDecimals = supportedDecimals;
    this.destination = destination;
  }
}
