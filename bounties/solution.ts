// src/utils/marketCap.ts
import { BigNumber, ethers } from "ethers";

/**
 * Information required to compute market cap for a USDC‑quoted pair.
 */
export interface PairInfo {
  /** Total token supply as a raw integer (including decimals). */
  totalSupply: BigNumber;
  /** Token decimals (e.g., 18 for most ERC‑20 tokens). */
  decimals: number;
  /** Current price of the token quoted in USDC (raw integer, 6 decimals). */
  priceInUSDC: BigNumber;
}

/**
 * Compute the market cap in USD for a token whose price is quoted in USDC.
 *
 * USDC has 6 decimals, so we treat `priceInUSDC` as a fixed‑point number with
 * 6 decimal places. The token supply is divided by 10**decimals to obtain the
 * human‑readable amount, then multiplied by the price.
 *
 * The result is returned as a string representing a decimal number with up to
 * 2 decimal places (rounded half‑up). If you need higher precision, adjust the
 * `outputDecimals` parameter.
 *
 * @param pair   Token data required for the calculation.
 * @param outputDecimals Number of decimal places in the final string (default 2).
 * @returns Market cap as a human‑readable decimal string.
 */
export function computeUSDCQuotedMarketCap(
  pair: PairInfo,
  outputDecimals: number = 2
): string {
  // 1. Convert totalSupply to a floating point representation.
  const supplyFloat = parseFloat(
    ethers.utils.formatUnits(pair.totalSupply, pair.decimals)
  );

  // 2. Convert priceInUSDC (6 decimals) to a floating point USD price.
  const priceFloat = parseFloat(
    ethers.utils.formatUnits(pair.priceInUSDC, 6) // USDC has 6 decimals
  );

  // 3. Market cap = supply * price.
  const rawMarketCap = supplyFloat * priceFloat;

  // 4. Round to the desired precision.
  const factor = Math.pow(10, outputDecimals);
  const rounded = Math.round(rawMarketCap * factor) / factor;

  // 5. Return as string with fixed decimals (trailing zeros kept).
  return rounded.toFixed(outputDecimals);
}

/* -------------------------------------------------------------------------- */
/* Example usage (remove or comment out in production)                        */
/* -------------------------------------------------------------------------- */
if (require.main === module) {
  // Example token: 1,000,000 tokens with 18 decimals, price = 2.5 USDC
  const examplePair: PairInfo = {
    totalSupply: ethers.BigNumber.from("1000000000000000000000000"), // 1,000,000 * 10^18
    decimals: 18,
    priceInUSDC: ethers.BigNumber.from("2500000"), // 2.5 USDC = 2.5 * 10^6
  };

  console.log("Market Cap (USD):", computeUSDCQuotedMarketCap(examplePair));
}