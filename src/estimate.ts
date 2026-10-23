import type { EstimateFeeParams, FeeEstimate, ChainId, TransferMode, TransferSpeed } from "./types.js";
import { ARC_DOMAIN, STELLAR_DOMAIN } from "./constants.js";
import { fetchFastTransferFeeBps } from "./iris/poll.js";
import { toRawAmount, fromRawAmount, decimalsForChain } from "./utils/amount.js";
import { parseUsdcAmount } from "./utils/encoding.js";

function domainFor(chain: ChainId): number {
  return chain === "arc" ? ARC_DOMAIN : STELLAR_DOMAIN;
}

// Arc's chain finality is sub-second, but Stellar's ~5s ledger close time and
// Iris attestation overhead dominate standard-transfer duration.
export const STANDARD_DURATION_SECONDS = 20;
export const FAST_DURATION_SECONDS = 15;

/**
 * Pure helper shared by estimateFee() and transfer() to decide whether a fast
 * transfer request stays fast or downgrades to standard based on maxWait and maxFee.
 */
export function resolveFastFallback(params: {
  speed: TransferSpeed;
  maxWait?: number;
  feeRaw?: bigint;
  maxFee?: string;
  sourceChain: ChainId;
}): { transferMode: TransferMode; feeRaw: bigint } {
  if (params.speed !== "fast") {
    return { transferMode: "standard", feeRaw: 0n };
  }
  if (params.maxWait !== undefined && FAST_DURATION_SECONDS > params.maxWait) {
    return { transferMode: "standard", feeRaw: 0n };
  }
  const feeRaw = params.feeRaw ?? 0n;
  if (params.maxFee !== undefined && params.feeRaw !== undefined) {
    const maxFeeRaw = parseUsdcAmount(params.maxFee, decimalsForChain(params.sourceChain));
    if (feeRaw > maxFeeRaw) {
      return { transferMode: "standard", feeRaw: 0n };
    }
  }
  return { transferMode: "fast", feeRaw };
}

export async function estimateFee(params: EstimateFeeParams): Promise<FeeEstimate> {
  const precheck = resolveFastFallback({
    speed: params.speed,
    maxWait: params.maxWait,
    sourceChain: params.from,
  });
  if (precheck.transferMode === "standard") {
    return {
      protocolFee: "0",
      estimatedDurationSeconds: STANDARD_DURATION_SECONDS,
      transferMode: "standard",
    };
  }

  const network = params.network ?? "mainnet";
  const feeBps = await fetchFastTransferFeeBps(
    domainFor(params.from),
    domainFor(params.to),
    network === "testnet",
  );

  const amountRaw = toRawAmount(params.amount, params.from);
  const quotedFeeRaw = (amountRaw * BigInt(feeBps)) / 10_000n;
  const resolved = resolveFastFallback({
    speed: params.speed,
    maxWait: params.maxWait,
    feeRaw: quotedFeeRaw,
    maxFee: params.maxFee,
    sourceChain: params.from,
  });

  if (resolved.transferMode === "standard") {
    return {
      protocolFee: "0",
      estimatedDurationSeconds: STANDARD_DURATION_SECONDS,
      transferMode: "standard",
    };
  }

  return {
    protocolFee: fromRawAmount(resolved.feeRaw, params.from),
    estimatedDurationSeconds: FAST_DURATION_SECONDS,
    transferMode: "fast",
  };
}
