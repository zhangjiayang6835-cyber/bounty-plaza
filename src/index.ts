export { transfer, completeMint, resolveBurn } from "./transfer.js";
export { estimateFee } from "./estimate.js";
export { getAttestation } from "./iris/poll.js";
export { decodeCctpMessage } from "./utils/message.js";
export { decodeStellarForwardHook, convertPrecision } from "./utils/encoding.js";
export { decimalsForChain } from "./utils/amount.js";
export { arcTestnetChain, arcMainnetChain } from "./chains/arc.js";
export { checkStellarRecipientReady } from "./chains/stellar.js";
// Re-exported so a consumer building a StellarSigner does not have to add @stellar/stellar-sdk
// as a second direct dependency. Two copies of that package at different versions produce
// structurally similar but distinct Keypair types, which the compiler cannot reconcile and
// which only surfaces in the signing path at runtime. Importing it from here keeps one copy.
export { Keypair } from "@stellar/stellar-sdk";
export { ARC_TESTNET, ARC_MAINNET, STELLAR_TESTNET, STELLAR_MAINNET } from "./constants.js";
export {
  TransferError,
  SubmissionTimeoutError,
  AttestationNotReadyError,
  IrisRequestError,
  AmountPrecisionError,
} from "./errors.js";
export type { TransferErrorCode } from "./errors.js";
export type { StellarRecipientStatus, StellarRetryOptions } from "./chains/stellar.js";
export type {
  ChainId,
  Network,
  TransferSpeed,
  TransferMode,
  TransferStatus,
  TransferProgressEvent,
  ArcSigner,
  StellarSigner,
  StellarSignFunction,
  Signer,
  TransferOptions,
  TransferOptionsBase,
  ArcDestinationOptions,
  StellarDestinationOptions,
  TransferParams,
  TransferResult,
  EstimateFeeParams,
  FeeEstimate,
  CompleteMintParams,
  CompleteMintOptions,
  CompleteMintResult,
  ResolveBurnParams,
  ResolvedBurn,
  CctpBurnMessage,
  TransferProgressStage,
  TransferProgressEvent,
  RecipientCheckProgressEvent,
  ApproveProgressEvent,
  BurnSubmittedProgressEvent,
  BurnConfirmedProgressEvent,
  AttestationProgressEvent,
  MintSubmittedProgressEvent,
  MintConfirmedProgressEvent,
} from "./types.js";
