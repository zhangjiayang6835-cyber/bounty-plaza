// src/utils/marketCap.ts

import { BigNumber, utils } from 'ethers';

/**
 * Normalizes a numeric value to a BigNumber with the given decimals.
 * @param value - The numeric value (string or number).
 * @param decimals - Number of decimals the value should be represented with.
 * @returns BigNumber representation.
 */
function toBigNumber(value: string | number, decimals: number): BigNumber {
  return utils.parseUnits(value.toString(), decimals);
}

/**
 * Computes the market cap for a token pair.
 *
 * @param price - The price of the base token expressed in the quote token (e.g., USDC).
 * @param priceDecimals - Decimals of the price (USDC uses 6, most other tokens use 18).
 * @param totalSupply - Total supply of the base token.
 * @param supplyDecimals - Decimals of the total supply (usually 18).
 * @returns Market cap as a string in USD (or the quote token's fiat equivalent) with 2 decimal places.
 *
 * Example:
 *   // USDC‑quoted pair (price has 6 decimals)
 *   getMarketCap('1.234567', 6, '1000000', 18) => '1234567.00'
 */
export function getMarketCap(
  price: string | number,
  priceDecimals: number,
  totalSupply: string | number,
  supplyDecimals: number
): string {
  // Convert inputs to BigNumber with proper scaling
  const priceBN = toBigNumber(price, priceDecimals);
  const supplyBN = toBigNumber(totalSupply, supplyDecimals);

  // marketCapRaw = price * supply / (10 ** (priceDecimals + supplyDecimals))
  const denominator = BigNumber.from(10).pow(priceDecimals + supplyDecimals);
  const marketCapRaw = priceBN.mul(supplyBN).div(denominator);

  // Convert back to a human‑readable string with 2 decimal places
  // Since marketCapRaw is already in quote token units (e.g., USDC with 6 decimals),
  // we format it using the quote token's decimals.
  const formatted = utils.formatUnits(marketCapRaw, priceDecimals);
  // Ensure exactly two decimal places
  const [intPart, fracPart = ''] = formatted.split('.');
  const roundedFrac = (fracPart + '00').slice(0, 2);
  return `${intPart}.${roundedFrac}`;
}

/**
 * Helper to automatically detect USDC‑quoted pairs.
 *
 * @param price - Price of the base token.
 * @param totalSupply - Total supply of the base token.
 * @param quoteTokenSymbol - Symbol of the quote token (e.g., 'USDC', 'USDT', 'USD').
 * @returns Market cap string.
 */
export function getMarketCapForPair(
  price: string | number,
  totalSupply: string | number,
  quoteTokenSymbol: string
): string {
  // USDC (and USDT) are 6‑decimal stablecoins; default to 18 otherwise.
  const priceDecimals = ['USDC', 'USDT', 'USD'].includes(quoteTokenSymbol.toUpperCase())
    ? 6
    : 18;

  // Assume base token follows the common 18‑decimal ERC‑20 standard.
  const supplyDecimals = 18;

  return getMarketCap(price, priceDecimals, totalSupply, supplyDecimals);
}