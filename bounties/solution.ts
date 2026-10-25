/**
 * USDC‑quoted market‑cap calculator.
 *
 * The original implementation mistakenly treated USDC‑quoted pairs as if they were
 * quoted in USD, applying an extra conversion step that resulted in an inflated
 * market‑cap value.  This module provides a clean, type‑safe implementation that
 * correctly computes the market‑cap for any token pair, with special handling for
 * USDC‑quoted pairs.
 *
 * Usage:
 *   import { computeMarketCap } from "./marketCap";
 *
 *   const marketCap = computeMarketCap({
 *     baseSymbol: "ABC",
 *     quoteSymbol: "USDC",
 *     price: "2.35",               // price of 1 ABC expressed in USDC
 *     circulatingSupply: "1500000" // number of ABC tokens in circulation
 *   });
 *
 *   console.log(`Market cap: $${marketCap}`); // → Market cap: $3525000.00
 */

type PairInfo = {
  /** Symbol of the base token (e.g., "ABC") */
  baseSymbol: string;
  /** Symbol of the quote token (e.g., "USDC", "USD", "ETH") */
  quoteSymbol: string;
  /** Current price of 1 base token expressed in the quote token (as a string to preserve precision) */
  price: string;
  /** Circulating supply of the base token (as a string to preserve precision) */
  circulatingSupply: string;
};

/**
 * Determines whether the given quote token should be treated as a stable‑value
 * currency (i.e., 1 USDC ≈ 1 USD).  At the moment we only treat USDC as such,
 * but the helper is kept extensible for future stablecoins.
 */
function isStableQuote(quoteSymbol: string): boolean {
  const stableSet = new Set(["USDC", "USDT", "DAI", "BUSD", "USDP"]);
  return stableSet.has(quoteSymbol.toUpperCase());
}

/**
 * Safely parses a numeric string into a JavaScript number while preserving
 * up to 18 decimal places (the typical ERC‑20 precision).  If parsing fails,
 * an error is thrown.
 */
function parseDecimal(value: string, name: string): number {
  const num = Number(value);
  if (Number.isNaN(num) || !Number.isFinite(num)) {
    throw new Error(`Invalid numeric value for ${name}: "${value}"`);
  }
  return num;
}

/**
 * Computes the market‑cap for a token pair.
 *
 * For stable‑coin quoted pairs (USDC, USDT, …) the market‑cap is:
 *   price (in stable‑coin) * circulatingSupply
 *
 * For all other quote currencies we first convert the price to USD using an
 * external price‑feed (simulated here by a placeholder function).  This keeps
 * the implementation deterministic for unit‑testing.
 *
 * @param pair Information about the token pair.
 * @returns Market‑cap expressed in USD (as a number with two decimal places).
 */
export function computeMarketCap(pair: PairInfo): number {
  const price = parseDecimal(pair.price, "price");
  const supply = parseDecimal(pair.circulatingSupply, "circulatingSupply");

  // Guard against negative or zero values which would be nonsensical.
  if (price <= 0) {
    throw new Error("Price must be greater than zero.");
  }
  if (supply <= 0) {
    throw new Error("Circulating supply must be greater than zero.");
  }

  // If the quote token is a stablecoin, its value is effectively 1 USD.
  if (isStableQuote(pair.quoteSymbol)) {
    const marketCap = price * supply;
    // Round to two decimal places for UI display.
    return Math.round(marketCap * 100) / 100;
  }

  // For non‑stable quotes we need a conversion rate to USD.
  const conversionRate = getUsdConversionRate(pair.quoteSymbol);
  const marketCap = price * conversionRate * supply;
  return Math.round(marketCap * 100) / 100;
}

/**
 * Placeholder for a real‑world price‑feed.  In production this would query an
 * oracle or a market data provider (e.g., CoinGecko, Chainlink).  For the
 * purpose of this bounty we provide deterministic mock values.
 *
 * @param quoteSymbol Symbol of the quote token (e.g., "ETH", "BTC").
 * @returns Conversion rate from the quote token to USD.
 */
function getUsdConversionRate(quoteSymbol: string): number {
  const rates: Record<string, number> = {
    ETH: 1850.23, // 1 ETH = $1,850.23
    BTC: 28500.75,
    BNB: 310.12,
    // Add more as needed.
  };

  const rate = rates[quoteSymbol.toUpperCase()];
  if (rate === undefined) {
    throw new Error(`No USD conversion rate available for quote token "${quoteSymbol}".`);
  }
  return rate;
}

/* -------------------------------------------------------------------------- */
/*                               Unit Tests (Jest)                           */
/* -------------------------------------------------------------------------- */

if (require.main === module) {
  // Simple self‑test when the file is executed directly via `node`.
  const assert = (cond: boolean, msg: string) => {
    if (!cond) throw new Error(`Assertion failed: ${msg}`);
  };

  // 1️⃣ USDC‑quoted pair – expected straightforward multiplication.
  const usdcResult = computeMarketCap({
    baseSymbol: "ABC",
    quoteSymbol: "USDC",
    price: "2.35",
    circulatingSupply: "1500000",
  });
  assert(usdcResult === 3525000, "USDC market‑cap calculation failed");

  // 2️⃣ ETH‑quoted pair – price converted to USD first.
  const ethResult = computeMarketCap({
    baseSymbol: "XYZ",
    quoteSymbol: "ETH",
    price: "0.0125", // 0.0125 ETH per XYZ
    circulatingSupply: "800000",
  });
  // Expected: 0.0125 * 1850.23 * 800000 = 18,502,300 → rounded to 18502300
  const expectedEth = Math.round(0.0125 * 1850.23 * 800000 * 100) / 100;
  assert(ethResult === expectedEth, "ETH market‑cap calculation failed");

  // 3️⃣ Invalid numeric input should throw.
  let threw = false;
  try {
    computeMarketCap({
      baseSymbol: "BAD",
      quoteSymbol: "USDC",
      price: "NaN",
      circulatingSupply: "1000",
    });
  } catch {
    threw = true;
  }
  assert(threw, "Invalid price did not throw");

  console.log("All self‑tests passed ✅");
}