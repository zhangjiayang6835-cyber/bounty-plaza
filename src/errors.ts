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
  /**
   * Machine-readable discriminator for the wrapped failure, set when the underlying error
   * has a type a caller can act on. `"ATTESTATION_NOT_READY"` means the burn is real and
   * the attestation simply has not arrived yet, so the caller should retry rather than
   * treat the transfer as lost. Undefined for failures with no more specific classification.
   */
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
      `Amount ${amount} has ${precision} significant decimal places, but ${destination} supports only ${supportedDecimals}`,
    );
    this.name = "AmountPrecisionError";
    this.amount = amount;
    this.precision = precision;
    this.supportedDecimals = supportedDecimals;
    this.destination = destination;
  }
}

/**
 * Thrown when a burn has been confirmed on the source chain but Circle has not attested it
 * yet. This is a retryable state rather than a failure: the burn is real, the funds are
 * safe, and the attestation normally arrives within minutes. A service needs to tell this
 * apart from a genuine error because it answers a client with a retryable status in one
 * case and a terminal one in the other, and matching on message text is not a stable
 * contract.
 *
 * Carries burnTxHash so the caller can retry with completeMint() after a delay.
 */
export class AttestationNotReadyError extends Error {
  readonly burnTxHash: string;

  constructor(message: string, burnTxHash: string) {
    super(message);
    this.name = "AttestationNotReadyError";
    this.burnTxHash = burnTxHash;
  }
}

/**
 * Thrown when Circle's Iris service returned a response that polling cannot recover from,
 * such as a 5xx. Without this, a persistent Iris outage is indistinguishable from Circle
 * being slow, and the caller only learns something is wrong when the poll window expires.
 */
export class IrisRequestError extends Error {
  /** HTTP status, or undefined when the request failed before a response arrived. */
  readonly status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "IrisRequestError";
    this.status = status;
  }
}

/**
 * Thrown when a transaction was broadcast (a hash exists) but the SDK gave up waiting
 * for on-chain confirmation before it could tell whether it landed. This is genuine
 * uncertainty, not "nothing happened": the transaction may still succeed or fail on
 * its own. Chain-specific submit helpers (writeAndWait on Arc, pollTransactionStatus on
 * Stellar) throw this instead of a bare Error so callers with a hash can act on it,
 * rather than the hash being silently discarded along with the thrown error.
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
 * Thrown before any approve or burn when the requested transfer amount carries more
 * significant decimal places than the destination chain's USDC supports.
 */
export class AmountPrecisionError extends Error {
  readonly amount: string;
  readonly precision: number;
  readonly supportedDecimals: number;
  readonly destination: ChainId;

  constructor(
    amount: string,
    precision: number,
    supportedDecimals: number,
    destination: ChainId,
  ) {
    super(
      `Amount ${amount} has ${precision} significant decimal places, exceeding the ${supportedDecimals} decimal places supported on ${destination}`,
    );
    this.name = "AmountPrecisionError";
    this.amount = amount;
    this.precision = precision;
    this.supportedDecimals = supportedDecimals;
    this.destination = destination;
  }
}
