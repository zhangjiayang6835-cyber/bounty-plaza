import type { WalletClient } from "viem";
import type { Keypair } from "@stellar/stellar-sdk";
import type { CctpBurnMessage } from "./utils/message.js";

export type { CctpBurnMessage };

export type ChainId = "arc" | "stellar";
/** Which deployment to transact against. Defaults to "mainnet" wherever it is accepted. */
export type Network = "mainnet" | "testnet";
export type TransferSpeed = "standard" | "fast";
export type TransferMode = "standard" | "fast";
export type TransferStatus = "success" | "pending" | "failed";

/** Signs Arc (EVM) transactions. Wraps a viem WalletClient with an account attached. */
export interface ArcSigner {
  walletClient: WalletClient;
}

/** Signs a prepared Stellar transaction XDR and returns the signed XDR. */
export type StellarSignFunction = (xdr: string, networkPassphrase: string) => Promise<string>;

/**
 * Signs Stellar transactions. `publicKey` is always required. At least one signing route
 * must also be supplied, either a Keypair held in process or a custom sign function for a
 * hardware wallet or an external signer, so the "neither was provided" case is a compile
 * error rather than a throw discovered after a Soroban round trip.
 *
 * Supplying both is allowed; signTransaction is then preferred.
 */
export type StellarSigner = { publicKey: string } & (
  | { keypair: Keypair; signTransaction?: StellarSignFunction }
  | { keypair?: undefined; signTransaction: StellarSignFunction }
);

export type Signer = ArcSigner | StellarSigner;

/**
 * Individual stages emitted throughout a transfer lifecycle.
 */
export type TransferProgressStage =
  | "recipient-check"
  | "approve"
  | "burn-submitted"
  | "burn-confirmed"
  | "attestation"
  | "mint-submitted"
  | "mint-confirmed";

/**
 * Emitted before validating that a Stellar destination account exists and holds
 * a USDC trustline (Arc -> Stellar transfers only).
 */
export interface RecipientCheckProgressEvent {
  stage: "recipient-check";
  timestamp: number;
}

/**
 * Emitted before submitting the token approval transaction on the source chain.
 */
export interface ApproveProgressEvent {
  stage: "approve";
  timestamp: number;
}

/**
 * Emitted once the source chain burn transaction has been broadcast.
 */
export interface BurnSubmittedProgressEvent {
  stage: "burn-submitted";
  burnTxHash: string;
  timestamp: number;
}

/**
 * Emitted once the source chain burn transaction has confirmed on-chain.
 */
export interface BurnConfirmedProgressEvent {
  stage: "burn-confirmed";
  burnTxHash: string;
  timestamp: number;
}

/**
 * Emitted before polling Circle's Iris service for the attestation signature.
 */
export interface AttestationProgressEvent {
  stage: "attestation";
  burnTxHash: string;
  attestationHash?: string;
  timestamp: number;
}

/**
 * Emitted immediately before broadcasting the destination chain mint transaction.
 */
export interface MintSubmittedProgressEvent {
  stage: "mint-submitted";
  burnTxHash: string;
  attestationHash?: string;
  mintTxHash?: string;
  timestamp: number;
}

/**
 * Emitted once the destination chain mint transaction has confirmed on-chain.
 */
export interface MintConfirmedProgressEvent {
  stage: "mint-confirmed";
  burnTxHash: string;
  attestationHash: string;
  mintTxHash: string;
  timestamp: number;
}

/**
 * Discriminated union of all transfer lifecycle progress events.
 */
export type TransferProgressEvent =
  | RecipientCheckProgressEvent
  | ApproveProgressEvent
  | BurnSubmittedProgressEvent
  | BurnConfirmedProgressEvent
  | AttestationProgressEvent
  | MintSubmittedProgressEvent
  | MintConfirmedProgressEvent;

export interface TransferOptionsBase {
  /** Optional callback invoked as the transfer progresses through distinct lifecycle stages. Exceptions thrown by this callback are safely swallowed to avoid disrupting the in-flight transfer. */
  onProgress?: (event: TransferProgressEvent) => void;
  /** Optional AbortSignal to cancel in-flight polling loops and operations. */
  signal?: AbortSignal;
  /** Max USDC fee tolerated for a fast transfer. Falls back to standard if the quoted fee exceeds this. */
  maxFee?: string;
  /** Max seconds to wait before falling back to standard transfer. */
  maxWait?: number;
  /** Milliseconds between Iris attestation polls. Default 3000. */
  pollInterval?: number;
  /** Milliseconds before polling gives up. Default 300000. */
  pollTimeout?: number;
  /** Number of attempts for Stellar allowance/RPC retry loops. Defaults to 6 for allowance polling and 3 for burn submission. */
  stellarRetryAttempts?: number;
  /** Delay between Stellar allowance/RPC retry attempts in milliseconds. Defaults to 1500ms and 2000ms respectively. */
  stellarRetryDelayMs?: number;
  /**
   * Overrides the Stellar Soroban RPC URL. The mainnet default endpoint is
   * rate-limited; supply your own provider for real usage. No effect on Arc.
   */
  stellarRpcUrl?: string;
  /**
   * Overrides the Arc RPC URL. Only used for reading receipts; the signer's own
   * client broadcasts. No effect on Stellar.
   */
  arcRpcUrl?: string;
  /**
   * Maximum attempts for Stellar post-approval allowance polling (`waitForAllowance`, default 6)
   * and transient RPC-lag retries during `deposit_for_burn` (`retryOnTransientRpcLag`, default 3).
   * Must be a positive integer when provided. No effect when the source chain is Arc.
   */
  stellarRetryAttempts?: number;
  /**
   * Delay in milliseconds between attempts for Stellar post-approval allowance polling
   * (`waitForAllowance`, default 1500) and transient RPC-lag retries during `deposit_for_burn`
   * (`retryOnTransientRpcLag`, default 2000). Must be a non-negative number when provided.
   * No effect when the source chain is Arc.
   */
  stellarRetryDelayMs?: number;
}

/**
 * Options for a transfer whose destination is Arc. `destinationSigner`, when present, is the
 * Arc signer that submits receiveMessage.
 */
export interface ArcDestinationOptions extends TransferOptionsBase {
  /**
   * Signer for the destination-chain completion call, submit by receiveMessage on Arc. This is
   * a separate signature from `signer` because completing a CCTP transfer requires paying gas
   * natively on the destination chain, which the source-chain signer cannot do. Omit this to
   * perform only the burn and attestation steps: the result comes back with status "pending"
   * and an empty mintTxHash. Call completeMint() with burnTxHash and a destination-chain
   * signer to finish it later (e.g. from a backend process holding the destination key).
   */
  destinationSigner?: ArcSigner;
}

/**
 * Options for a transfer whose destination is Stellar. `destinationSigner`, when present, is
 * the Stellar signer that submits mint_and_forward.
 */
export interface StellarDestinationOptions extends TransferOptionsBase {
  /** Signer for the destination-chain completion call, submit by mint_and_forward on Stellar. */
  destinationSigner?: StellarSigner;
}

export type TransferOptions = ArcDestinationOptions | StellarDestinationOptions;

/**
 * Parameters for transfer(). The direction decides which signers are required: a transfer
 * burns on its source chain, so `signer` must be native to `from`, and it mints on its
 * destination chain, so `options.destinationSigner` must be native to `to`. Naming a signer
 * for the wrong chain is a compile error rather than a failure after the burn.
 */
export type TransferParams = TransferParamsBase &
  (
    | { from: "arc"; to: "stellar"; signer: ArcSigner; options?: StellarDestinationOptions }
    | { from: "stellar"; to: "arc"; signer: StellarSigner; options?: ArcDestinationOptions }
  );

interface TransferParamsBase {
  amount: string;
  recipient: string;
  speed: TransferSpeed;
  /** Which deployment to transact against. Default "mainnet". */
  network?: Network;
}

export interface TransferResult {
  status: TransferStatus;
  transferMode: TransferMode;
  burnTxHash: string;
  attestationHash: string;
  mintTxHash: string;
  fee: string;
  durationMs: number;
}

export interface EstimateFeeParams {
  from: ChainId;
  to: ChainId;
  amount: string;
  speed: TransferSpeed;
  /** Max USDC fee tolerated for a fast transfer; falls back to standard if exceeded. */
  maxFee?: string;
  /** Max seconds to wait before falling back to standard transfer. */
  maxWait?: number;
  /** Which deployment to quote against. Default "mainnet". */
  network?: Network;
}

export interface FeeEstimate {
  protocolFee: string;
  estimatedDurationSeconds: number;
  transferMode: TransferMode;
}

/**
 * Knobs for the completion step. Mirrors TransferOptions where the two overlap, so a
 * caller that already holds a TransferOptions-shaped object can reuse it.
 */
export interface CompleteMintOptions {
  /** Optional callback invoked as the mint progresses through distinct lifecycle stages. */
  onProgress?: (event: TransferProgressEvent) => void;
  /** Optional AbortSignal to cancel in-flight attestation polling. */
  signal?: AbortSignal;
  /** Milliseconds between Iris attestation polls. Default 3000. */
  pollInterval?: number;
  /** Milliseconds before polling gives up. Default 300000. */
  pollTimeout?: number;
  /**
   * Overrides the Stellar Soroban RPC URL. The mainnet default endpoint is
   * rate-limited; supply your own provider for real usage. No effect on Arc.
   */
  stellarRpcUrl?: string;
  /** Overrides the Arc RPC URL. No effect on Stellar. */
  arcRpcUrl?: string;
}

/**
 * Parameters for completeMint(). The mint runs on `to`, so `signer` must be native to
 * `to`, which is what the direction pair pins down at compile time.
 */
export type CompleteMintParams = CompleteMintParamsBase &
  (
    | { from: "arc"; to: "stellar"; signer: StellarSigner }
    | { from: "stellar"; to: "arc"; signer: ArcSigner }
  );

interface CompleteMintParamsBase {
  /** The burnTxHash returned by the earlier pending transfer() call. */
  burnTxHash: string;
  /** Which deployment the original transfer ran on. Default "mainnet". */
  network?: Network;
  /** Polling and RPC knobs. Preferred over the top-level equivalents below. */
  options?: CompleteMintOptions;
  /** Optional AbortSignal to cancel in-flight attestation polling. */
  signal?: AbortSignal;
  /** Milliseconds between Iris attestation polls. Default 3000. */
  pollInterval?: number;
  /** Milliseconds before polling gives up. Default 300000. */
  pollTimeout?: number;
  /** Overrides the Stellar Soroban RPC URL. No effect on Arc. */
  stellarRpcUrl?: string;
  /** Overrides the Arc RPC URL. No effect on Stellar. */
  arcRpcUrl?: string;
}

export interface CompleteMintResult {
  mintTxHash: string;
  attestationHash: string;
}

export interface ResolveBurnParams {
  /** The chain the burn happened on (the "from" of the original transfer). */
  from: ChainId;
  /** The burn transaction hash, whether this SDK produced it or not. */
  burnTxHash: string;
  /** Which deployment the burn happened on. Default "mainnet". */
  network?: Network;
  /** Optional AbortSignal to cancel network reads. */
  signal?: AbortSignal;
}

/**
 * What a burn has already committed to, read back from Circle's attestation message. For a
 * Stellar-bound burn, `forwardRecipient` is the account the mint will actually pay, which
 * is the only way to know it without trusting a caller-supplied value.
 */
export interface ResolvedBurn extends CctpBurnMessage {
  /** Circle's attestation for the burn, or null while it is still pending. */
  attestation: string | null;
}
