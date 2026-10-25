/**
 * USDC Market Cap Calculator
 *
 * This module provides utilities to correctly calculate the market cap for token pairs
 * that are quoted in USDC. The market cap is defined as:
 *
 *   marketCap (USD) = tokenPrice (USD) * circulatingSupply (tokens)
 *
 * For USDC‑quoted pairs the token price is already expressed in USD, so the calculation
 * is straightforward. For other quote currencies we optionally allow a conversion rate
 * to USDC to still obtain a USD market cap.
 *
 * The main exported function is `calculateMarketCap`.
 *
 * Usage:
 *   const marketCap = calculateMarketCap({
 *     base: "ABC",
 *     quote: "USDC",
 *   }, 2.5, 1_000_000);
 *
 *   // marketCap === 2_500_000
 */

type TokenPair = {
  /** Symbol of the base token (the asset whose price we are quoting) */
  base: string;
  /** Symbol of the quote token (the currency in which the price is expressed) */
  quote: string;
};

/**
 * Options for market‑cap calculation.
 */
interface MarketCapOptions {
  /** Price of one unit of the base token expressed in the quote currency. */
  price: number;
  /** Circulating supply of the base token (in token units). */
  supply: number;
  /**
   * Optional conversion rate from the quote currency to USDC.
   *
   * - If omitted and the quote is USDC, the conversion factor defaults to 1.
   * - If the quote is not USDC and no conversion rate is supplied, the function
   *   throws because it cannot express the market cap in USD.
   *
   * Example: If the pair is ETH/USDT and 1 USDT = 0.9995 USDC, pass
   * `quoteToUSDC = 0.9995`.
   */
  quoteToUSDC?: number;
}

/**
 * Calculates the market cap (in USD) for a given token pair.
 *
 * @param pair   The token pair (base/quote).
 * @param opts   Pricing and supply information.
 *
 * @returns The market cap expressed in USD.
 *
 * @throws If the quote token is not USDC and no conversion rate is supplied.
 */
export function calculateMarketCap(
  pair: TokenPair,
  opts: MarketCapOptions
): number {
  const { price, supply, quoteToUSDC } = opts;

  // Guard against nonsensical inputs.
  if (price <= 0) {
    throw new Error("Price must be a positive number.");
  }
  if (supply < 0) {
    throw new Error("Supply cannot be negative.");
  }

  // Determine the factor to convert the quoted price to USDC.
  // - If the quote token is USDC, the factor is 1.
  // - Otherwise we need an explicit conversion rate.
  const conversionFactor =
    pair.quote.toUpperCase() === "USDC"
      ? 1
      : quoteToUSDC !== undefined
      ? quoteToUSDC
      : undefined;

  if (conversionFactor === undefined) {
    throw new Error(
      `Quote token '${pair.quote}' is not USDC and no conversion rate was provided.`
    );
  }

  // Market cap in USD = price (quote per base) * conversionFactor (USDC per quote) * supply
  const marketCapUSD = price * conversionFactor * supply;

  // Ensure we return a finite number.
  if (!Number.isFinite(marketCapUSD)) {
    throw new Error("Calculated market cap is not a finite number.");
  }

  return marketCapUSD;
}

/* -------------------------------------------------------------------------- */
/*                               Unit Tests (Jest)                           */
/* -------------------------------------------------------------------------- */

if (require.main === module) {
  // Simple self‑test runner when executed directly via `node`.
  // In a real project you would place these in a separate *.test.ts file
  // and run them with Jest. This block allows quick verification without
  // additional tooling.

  const assert = (cond: boolean, msg: string) => {
    if (!cond) throw new Error(`Assertion failed: ${msg}`);
  };

  // 1. USDC‑quoted pair – straightforward case
  const cap1 = calculateMarketCap(
    { base: "ABC", quote: "USDC" },
    { price: 2.5, supply: 1_000_000 }
  );
  assert(cap1 === 2_500_000, "USDC‑quoted market cap incorrect");

  // 2. Non‑USDC quote with conversion rate
  const cap2 = calculateMarketCap(
    { base: "XYZ", quote: "USDT" },
    { price: 1.0, supply: 500_000, quoteToUSDC: 0.9995 }
  );
  // Expected: 1.0 * 0.9995 * 500_000 = 499_750
  assert(cap2 === 499_750, "Converted market cap incorrect");

  // 3. Zero supply should yield zero market cap
  const cap3 = calculateMarketCap(
    { base: "ZERO", quote: "USDC" },
    { price: 10, supply: 0 }
  );
  assert(cap3 === 0, "Zero supply market cap should be zero");

  // 4. Negative price should throw
  let threw = false;
  try {
    calculateMarketCap({ base: "BAD", quote: "USDC" }, { price: -1, supply: 100 });
  } catch (e) {
    threw = true;
  }
  assert(threw, "Negative price did not throw");

  // 5. Missing conversion rate for non‑USDC quote should throw
  threw = false;
  try {
    calculateMarketCap({ base: "BAD", quote: "EUR" }, { price: 1, supply: 100 });
  } catch (e) {
    threw = true;
  }
  assert(threw, "Missing conversion rate did not throw");

  console.log("All self‑tests passed.");
}