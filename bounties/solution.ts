// marketCapUtils.ts
import { BigNumber, ethers } from "ethers";

/**
 * Interface describing a token pair quoted in USDC.
 */
export interface Pair {
  /** Token symbol, e.g., "ABC" */
  tokenSymbol: string;
  /** Price of 1 token in USDC (as a decimal string, 6 decimals) */
  priceInUSDC: string;
  /** Total token supply (as a decimal string, token's own decimals) */
  totalSupply: string;
  /** Number of decimals the token uses */
  tokenDecimals: number;
  /** Existing (possibly incorrect) market cap string */
  marketCap?: string;
}

/**
 * Formats a USDC amount (BigNumber with 6 decimals) to a human‑readable string.
 * Keeps two decimal places and adds commas.
 */
function formatUSDC(value: BigNumber): string {
  const usdcDecimals = 6;
  const divisor = BigNumber.from(10).pow(usdcDecimals);
  const whole = value.div(divisor).toString();
  const fraction = value.mod(divisor).toString().padStart(usdcDecimals, "0").slice(0, 2); // two decimals
  // add commas to whole part
  const withCommas = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return `${withCommas}.${fraction}`;
}

/**
 * Computes the correct market cap for a USDC‑quoted pair.
 *
 * @param priceInUSDC  Price per token in USDC (6‑decimal string)
 * @param totalSupply  Total token supply (token‑decimals string)
 * @param tokenDecimals Number of decimals the token uses
 * @returns Market cap as a formatted USDC string
 */
export function computeMarketCap(
  priceInUSDC: string,
  totalSupply: string,
  tokenDecimals: number
): string {
  const usdcDecimals = 6;

  const priceBN = ethers.utils.parseUnits(priceInUSDC, usdcDecimals); // price * 10^6
  const supplyBN = ethers.utils.parseUnits(totalSupply, tokenDecimals); // supply * 10^tokenDecimals

  // marketCap (USDC, 6 decimals) = price * supply / 10^{tokenDecimals}
  const marketCapBN = priceBN.mul(supplyBN).div(BigNumber.from(10).pow(tokenDecimals));

  return formatUSDC(marketCapBN);
}

/**
 * Recalculates market caps for an array of USDC‑quoted pairs.
 * Returns a new array with corrected `marketCap` fields.
 *
 * @param pairs List of token pairs
 */
export function adjustMarketCapForPairs(pairs: Pair[]): Pair[] {
  return pairs.map((p) => {
    // Only adjust if price is quoted in USDC (we assume all input pairs are USDC‑quoted)
    const corrected = computeMarketCap(p.priceInUSDC, p.totalSupply, p.tokenDecimals);
    return { ...p, marketCap: corrected };
  });
}

/* ------------------- Example usage ------------------- */
// (Remove or comment out when integrating into the actual codebase)

if (require.main === module) {
  const examplePairs: Pair[] = [
    {
      tokenSymbol: "ABC",
      priceInUSDC: "1.234567", // $1.234567 per token
      totalSupply: "1000000", // 1,000,000 tokens
      tokenDecimals: 18,
    },
    {
      tokenSymbol: "XYZ",
      priceInUSDC: "0.050000", // $0.05 per token
      totalSupply: "50000000", // 50,000,000 tokens
      tokenDecimals: 8,
    },
  ];

  const updated = adjustMarketCapForPairs(examplePairs);
  console.log(updated);
}