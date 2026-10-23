import type { ChainId } from "../types.js";
import { ARC_MAINNET, STELLAR_MAINNET } from "../constants.js";
import { parseUsdcAmount, formatUsdcAmount } from "./encoding.js";
import { AmountPrecisionError } from "../errors.js";

/**
 * USDC's subunit precision is a property of the asset rather than of the deployment, so one
 * constant answers for both networks: Arc USDC has 6 decimals on testnet and mainnet alike,
 * Stellar USDC has 7 on both. Reading the mainnet constants here is deliberate and is not a
 * network selection.
 *
 * This is the ERC-20 / SEP-41 view of USDC. It is not the same scale as Arc's native
 * balance, which reports the same asset at 18 decimals; see README's "Amounts and decimals".
 */
export function decimalsForChain(chain: ChainId): number {
  return chain === "arc" ? ARC_MAINNET.usdcDecimals : STELLAR_MAINNET.usdcDecimals;
}

/** Parses a human-readable USDC amount into raw subunits native to the given chain. */
export function toRawAmount(amount: string, chain: ChainId): bigint {
  return parseUsdcAmount(amount, decimalsForChain(chain));
}

/** Formats raw subunits native to the given chain back into a human-readable USDC amount. */
export function fromRawAmount(raw: bigint, chain: ChainId): string {
  return formatUsdcAmount(raw, decimalsForChain(chain));
}

/**
 * Counts significant fractional decimal places in a human-readable USDC amount,
 * ignoring trailing zeros (e.g. "1.1230000" has 3 significant decimal places).
 */
export function significantDecimals(amount: string): number {
  const fraction = amount.split(".")[1] ?? "";
  return fraction.replace(/0+$/, "").length;
}

/**
 * Rejects an amount whose significant decimal precision exceeds what the destination
 * chain's USDC supports, before any approve or burn is submitted.
 */
export function assertDestinationPrecision(amount: string, destination: ChainId): void {
  const precision = significantDecimals(amount);
  const supportedDecimals = decimalsForChain(destination);
  if (precision > supportedDecimals) {
    throw new AmountPrecisionError(amount, precision, supportedDecimals, destination);
  }
}
