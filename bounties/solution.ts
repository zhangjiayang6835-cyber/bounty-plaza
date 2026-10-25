/**
 * USDC‑quoted market‑cap calculator
 *
 * The bug this module fixes:
 *   - For pairs quoted in USDC the market‑cap was calculated as
 *     `price * totalSupply` where `price` was interpreted as the amount of
 *     USDC per token **but** the total supply was not normalised to the token
 *     decimals. This resulted in a market‑cap that was off by a factor of
 *     10^decimals.
 *
 * This implementation normalises the total supply using the token's `decimals`
 * field before multiplying by the USDC price. The result is returned as a
 * string representing a decimal number with up to 18 fractional digits (the
 * typical precision for USDC).
 */

type PairInfo = {
  /** Symbol of the base token (e.g. "ABC") */
  baseSymbol: string;
  /** Symbol of the quote token – must be "USDC" for this calculator */
  quoteSymbol: string;
  /** Token price expressed in USDC (as a decimal string, e.g. "0.1234") */
  price: string;
  /** Total token supply as an integer string (raw units, not adjusted for decimals) */
  totalSupply: string;
  /** Number of decimals the base token uses (e.g. 18) */
  decimals: number;
};

/**
 * Normalises a raw integer amount using the token's decimals.
 *
 * @param raw   Raw integer amount (e.g. "1230000000000000000")
 * @param dec   Number of decimals (e.g. 18)
 * @returns     Decimal string with the appropriate fractional part.
 */
function normalizeAmount(raw: string, dec: number): string {
  // Ensure the string contains only digits
  if (!/^\d+$/.test(raw)) {
    throw new Error(`Invalid raw amount: ${raw}`);
  }

  // Pad with leading zeros to guarantee at least `dec` digits
  const padded = raw.padStart(dec + 1, '0');
  const integerPart = padded.slice(0, -dec);
  const fractionPart = padded.slice(-dec).replace(/0+$/g, ''); // trim trailing zeros

  return fractionPart ? `${integerPart}.${fractionPart}` : integerPart;
}

/**
 * Multiplies two decimal strings with arbitrary precision using bigint arithmetic.
 *
 * @param a Decimal string (e.g. "0.1234")
 * @param b Decimal string (e.g. "1000000")
 * @returns Decimal string representing a * b
 */
function multiplyDecimals(a: string, b: string): string {
  // Split into integer / fraction parts
  const [ai, af = ''] = a.split('.');
  const [bi, bf = ''] = b.split('.');

  const aDigits = ai + af;
  const bDigits = bi + bf;

  const aBig = BigInt(aDigits);
  const bBig = BigInt(bDigits);

  // Total number of fractional digits in the result
  const scale = af.length + bf.length;

  const product = aBig * bBig;
  const productStr = product.toString().padStart(scale + 1, '0');

  const integerPart = productStr.slice(0, -scale);
  const fractionPart = productStr.slice(-scale).replace(/0+$/g, '');

  return fractionPart ? `${integerPart}.${fractionPart}` : integerPart;
}

/**
 * Computes the market cap for a USDC‑quoted pair.
 *
 * @param pair Information about the pair.
 * @returns Market cap as a decimal string (USDC).
 *
 * @throws If the quote token is not USDC.
 */
export function computeUsdcMarketCap(pair: PairInfo): string {
  if (pair.quoteSymbol.toUpperCase() !== 'USDC') {
    throw new Error('This calculator only supports USDC‑quoted pairs.');
  }

  // Normalise total supply to a human‑readable decimal amount
  const normalizedSupply = normalizeAmount(pair.totalSupply, pair.decimals);

  // Multiply price (USDC per token) by the normalised supply
  const marketCap = multiplyDecimals(pair.price, normalizedSupply);

  return marketCap;
}

/* -------------------------------------------------------------------------- */
/*                               Example usage                               */
/* -------------------------------------------------------------------------- */

if (require.main === module) {
  // Example: token ABC with 18 decimals, total supply = 1,000,000 ABC (raw = 1e24)
  const examplePair: PairInfo = {
    baseSymbol: 'ABC',
    quoteSymbol: 'USDC',
    price: '0.123456',          // 0.123456 USDC per ABC
    totalSupply: '1000000000000000000000000', // 1,000,000 * 10^18
    decimals: 18,
  };

  console.log('Market cap (USDC):', computeUsdcMarketCap(examplePair));
}

/* -------------------------------------------------------------------------- */
/*                                   Tests                                    */
/* -------------------------------------------------------------------------- */

function assertEqual(actual: string, expected: string, msg?: string) {
  if (actual !== expected) {
    throw new Error(`Assertion failed${msg ? ': ' + msg : ''}\n  Expected: ${expected}\n  Got:      ${actual}`);
  }
}

// Test normalisation
assertEqual(normalizeAmount('1230000000000000000', 18), '1.23', 'normalizeAmount 1');
assertEqual(normalizeAmount('5000', 2), '50.00', 'normalizeAmount 2');
assertEqual(normalizeAmount('0', 6), '0', 'normalizeAmount zero');

// Test multiplication
assertEqual(multiplyDecimals('0.5', '2'), '1', 'multiply 0.5*2');
assertEqual(multiplyDecimals('1.23', '4.56'), '5.6088', 'multiply 1.23*4.56');
assertEqual(multiplyDecimals('100', '0.001'), '0.1', 'multiply 100*0.001');

// Test market‑cap calculation
const testPair: PairInfo = {
  baseSymbol: 'XYZ',
  quoteSymbol: 'USDC',
  price: '2.5',                     // 2.5 USDC per XYZ
  totalSupply: '2000000000000000000', // 2 XYZ (18 decimals)
  decimals: 18,
};
assertEqual(computeUsdcMarketCap(testPair), '5', 'market cap simple');

const testPair2: PairInfo = {
  baseSymbol: 'TOKEN',
  quoteSymbol: 'USDC',
  price: '0.000123',                // tiny price
  totalSupply: '1234567890123456789012345', // 1,234,567.890123456789012345 TOKEN
  decimals: 18,
};
assertEqual(
  computeUsdcMarketCap(testPair2),
  '152.345679012345679012345', // 0.000123 * 1,234,567.890123456789012345
  'market cap with many decimals'
);

console.log('All tests passed.');