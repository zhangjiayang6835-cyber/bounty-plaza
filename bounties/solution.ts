/**
 * USDC Market Cap Calculator
 *
 * This module provides a single exported function `calculateUsdcMarketCap`
 * that returns the correct market‑cap for any token pair quoted in USDC.
 *
 * USDC uses 6 decimal places.  Tokens can have an arbitrary number of
 * decimals (commonly 18).  Prices are usually expressed in USDC units
 * (i.e. 1 USDC = 1.000000).  To avoid floating‑point errors we perform
 * all arithmetic with `ethers.BigNumber` (integer arithmetic) and only
 * format the final result as a human‑readable decimal string.
 *
 * The function accepts:
 *   - `price`: the token price quoted in USDC (as string, number or BigNumber)
 *   - `priceDecimals`: decimals of the USDC price (default 6)
 *   - `supply`: the token's circulating supply (as string, number or BigNumber)
 *   - `supplyDecimals`: token's own decimals (default 18)
 *
 * It returns the market‑cap in USDC with 6 decimal places (as a string).
 */

import { BigNumber, FixedNumber } from 'ethers';

/**
 * Convert a numeric input (string | number | BigNumber) to a BigNumber
 * assuming the given number of decimals.
 */
function toBigNumber(
  value: string | number | BigNumber,
  decimals: number
): BigNumber {
  if (BigNumber.isBigNumber(value)) {
    return value;
  }
  // Ensure we work with a string to avoid JS floating point issues
  const str = typeof value === 'number' ? value.toString() : value;
  // Use FixedNumber for safe decimal handling, then convert to integer
  const fixed = FixedNumber.fromString(str);
  const scaled = fixed.mulUnsafe(FixedNumber.fromString(`1e${decimals}`));
  // FixedNumber may have a fractional part; we round down (as typical for on‑chain values)
  return BigNumber.from(scaled.floor().toString());
}

/**
 * Formats a BigNumber that represents a value with `decimals` decimal places
 * into a human‑readable decimal string (trims trailing zeros).
 */
function formatBigNumber(value: BigNumber, decimals: number): string {
  const factor = BigNumber.from(10).pow(decimals);
  const integerPart = value.div(factor).toString();
  const fractionPart = value.mod(factor).toString().padStart(decimals, '0');

  // Trim trailing zeros in the fractional part
  const trimmedFraction = fractionPart.replace(/0+$/g, '');
  return trimmedFraction ? `${integerPart}.${trimmedFraction}` : integerPart;
}

/**
 * Calculates the market cap (price * circulating supply) for a token whose
 * price is quoted in USDC.
 *
 * @param price            Token price quoted in USDC (e.g., "2.53")
 * @param priceDecimals    Decimals used by USDC (default 6)
 * @param supply           Circulating supply of the token (e.g., "1000000")
 * @param supplyDecimals   Token's own decimals (default 18)
 *
 * @returns Market cap in USDC as a decimal string with up to 6 decimals.
 */
export function calculateUsdcMarketCap(params: {
  price: string | number | BigNumber;
  priceDecimals?: number;   // USDC decimals, normally 6
  supply: string | number | BigNumber;
  supplyDecimals?: number;  // Token decimals, e.g., 18
}): string {
  const {
    price,
    priceDecimals = 6,
    supply,
    supplyDecimals = 18,
  } = params;

  // Convert inputs to integer representation
  const priceBN = toBigNumber(price, priceDecimals);      // price * 10^priceDecimals
  const supplyBN = toBigNumber(supply, supplyDecimals);   // supply * 10^supplyDecimals

  // Market cap (in raw integer) = priceBN * supplyBN / 10^priceDecimals
  // Explanation:
  //   priceBN = price * 10^priceDecimals
  //   supplyBN = supply * 10^supplyDecimals
  //   price * supply = (priceBN / 10^priceDecimals) * (supplyBN / 10^supplyDecimals)
  //   => marketCap = priceBN * supplyBN / (10^priceDecimals * 10^supplyDecimals)
  //   Since we want the result expressed in USDC (6 decimals), we multiply back by 10^priceDecimals.
  //   Final integer = priceBN * supplyBN / 10^supplyDecimals
  const denominator = BigNumber.from(10).pow(supplyDecimals);
  const rawMarketCap = priceBN.mul(supplyBN).div(denominator);

  // rawMarketCap now has `priceDecimals` decimals (USDC precision)
  return formatBigNumber(rawMarketCap, priceDecimals);
}

/* -------------------------------------------------------------------------- */
/* Example usage (can be removed in production)                               */
/* -------------------------------------------------------------------------- */
if (require.main === module) {
  // Example: Token price = 2.53 USDC, supply = 1,000,000 tokens (18 decimals)
  const mc = calculateUsdcMarketCap({
    price: '2.53',
    supply: '1000000',
    priceDecimals: 6,
    supplyDecimals: 18,
  });
  console.log('Market Cap (USDC):', mc); // Expected: "2530000"
}