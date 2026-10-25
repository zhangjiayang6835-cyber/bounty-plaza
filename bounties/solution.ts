// marketCap.ts
// Utility to correctly compute market‑cap for token pairs, especially USDC‑quoted pairs.

export interface TokenInfo {
  /** Token contract address (lower‑case) */
  address: string;
  /** Number of decimals used by the token */
  decimals: number;
  /** Human‑readable symbol, e.g. "USDC", "ETH" */
  symbol: string;
}

/** Minimal representation of a trading pair */
export interface Pair {
  /** Base token (the asset whose supply we consider) */
  base: TokenInfo;
  /** Quote token (the asset in which price is expressed) */
  quote: TokenInfo;
  /** Current price of 1 base token expressed in quote token units (raw, not scaled) */
  priceRaw: string; // e.g. "123456789" for 1.23456789 if quote has 8 decimals
  /** Total supply of the base token (raw, not scaled) */
  totalSupplyRaw: string; // e.g. "1000000000000000000" for 1 token with 18 decimals
}

/**
 * Normalises a raw integer string to a floating point number using token decimals.
 * @param raw   Raw integer string from blockchain (e.g. "123456789")
 * @param decimals Number of decimals the token uses
 * @returns Number in human readable format
 */
function normalize(raw: string, decimals: number): number {
  const divisor = Math.pow(10, decimals);
  return Number(raw) / divisor;
}

/**
 * Determines whether the given token is USDC (case‑insensitive address match).
 * Adjust the address list if you support multiple USDC deployments.
 */
function isUSDC(token: TokenInfo): boolean {
  const usdcAddresses = new Set([
    // Mainnet USDC
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
    // Testnet / other deployments can be added here
  ]);
  return usdcAddresses.has(token.address.toLowerCase());
}

/**
 * Computes the market‑cap in USD for a given pair.
 *
 * For USDC‑quoted pairs the quote token is already USD‑stable, so we can
 * directly multiply the base token supply (in human units) by the price
 * (also in USD). For other quote tokens we first convert the price to USD
 * using the quote token's USD price (provided via `quoteUsdPrice`).
 *
 * @param pair The trading pair data
 * @param quoteUsdPrice Current USD price of the quote token (if not USDC)
 * @returns Market‑cap in USD (rounded to 2 decimals)
 */
export function computeMarketCap(
  pair: Pair,
  quoteUsdPrice: number = 1 // default 1 for USDC‑quoted pairs
): number {
  // Normalise price and supply to human readable numbers
  const priceInQuote = normalize(pair.priceRaw, pair.quote.decimals);
  const supplyInBase = normalize(pair.totalSupplyRaw, pair.base.decimals);

  // If quote token is USDC, its USD price is 1 by definition.
  const effectiveQuoteUsdPrice = isUSDC(pair.quote) ? 1 : quoteUsdPrice;

  // Market‑cap = supply * price * quoteUsdPrice
  const marketCap = supplyInBase * priceInQuote * effectiveQuoteUsdPrice;

  // Round to 2 decimal places for UI friendliness
  return Math.round(marketCap * 100) / 100;
}

/* -------------------------------------------------------------------------- */
/* Example usage (remove or comment out in production)                        */
/* -------------------------------------------------------------------------- */
if (require.main === module) {
  const usdc: TokenInfo = {
    address: "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
    decimals: 6,
    symbol: "USDC",
  };
  const eth: TokenInfo = {
    address: "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
    decimals: 18,
    symbol: "ETH",
  };

  const ethUsdcPair: Pair = {
    base: eth,
    quote: usdc,
    priceRaw: "1800000", // 1.8 USDC (6 decimals) => $1.80
    totalSupplyRaw: "5000000000000000000", // 5 ETH (18 decimals)
  };

  console.log("ETH‑USDC market cap (USD):", computeMarketCap(ethUsdcPair));
}