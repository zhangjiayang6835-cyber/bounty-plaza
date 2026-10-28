"""Unit tests for issue #4109: USDC-quoted pair market cap and decimal scaling."""

import unittest
from solutions.issue_4109.usdc_marketcap import (
    USDC_MINT,
    WSOL_MINT,
    calculate_marketcap,
    get_quote_decimals,
    get_quote_to_usd_rate,
    normalize_dex_pair,
)


class TestUsdcMarketcap(unittest.TestCase):
    """Test suite for USDC quoted pairs marketcap calculations."""

    def test_usdc_decimal_lookup(self):
        self.assertEqual(get_quote_decimals(USDC_MINT), 6)
        self.assertEqual(get_quote_decimals("USDC"), 6)
        self.assertEqual(get_quote_decimals(WSOL_MINT), 9)
        self.assertEqual(get_quote_decimals("SOL"), 9)

    def test_quote_to_usd_rate(self):
        self.assertEqual(get_quote_to_usd_rate(USDC_MINT), 1.0)
        self.assertEqual(get_quote_to_usd_rate("USDC"), 1.0)
        self.assertEqual(get_quote_to_usd_rate(WSOL_MINT, sol_price_usd=180.0), 180.0)
        self.assertIsNone(get_quote_to_usd_rate(WSOL_MINT, sol_price_usd=None))

    def test_usdc_quoted_pair_marketcap_calculation(self):
        # 1,000,000,000 total supply (6 decimals) = 1e9 * 1e6 raw
        total_supply_raw = 1_000_000_000 * 1_000_000
        # Base reserve: 200,000,000 tokens (raw = 200M * 1e6)
        base_reserve_raw = 200_000_000 * 1_000_000
        # Quote reserve in USDC: 10,000 USDC (raw = 10,000 * 1e6)
        quote_reserve_raw = 10_000 * 1_000_000

        res = calculate_marketcap(
            base_reserve_raw=base_reserve_raw,
            quote_reserve_raw=quote_reserve_raw,
            total_supply_raw=total_supply_raw,
            quote_mint_or_symbol=USDC_MINT,
            base_decimals=6,
        )

        self.assertTrue(res["valid"])
        self.assertTrue(res["is_usdc_quoted"])
        # Expected price: 10,000 / 200,000,000 = $0.00005
        self.assertAlmostEqual(res["price_quote"], 0.00005)
        self.assertAlmostEqual(res["price_usd"], 0.00005)
        # Expected market cap: $0.00005 * 1,000,000,000 = $50,000
        self.assertAlmostEqual(res["market_cap_usd"], 50000.0)

    def test_wsol_quoted_pair_marketcap_calculation(self):
        # 1,000,000,000 total supply (6 decimals)
        total_supply_raw = 1_000_000_000 * 1_000_000
        base_reserve_raw = 200_000_000 * 1_000_000
        # Quote reserve in WSOL: 100 SOL (raw = 100 * 1e9 lamports)
        quote_reserve_raw = 100 * 1_000_000_000

        res = calculate_marketcap(
            base_reserve_raw=base_reserve_raw,
            quote_reserve_raw=quote_reserve_raw,
            total_supply_raw=total_supply_raw,
            quote_mint_or_symbol=WSOL_MINT,
            base_decimals=6,
            sol_price_usd=200.0,
        )

        self.assertTrue(res["valid"])
        self.assertFalse(res["is_usdc_quoted"])
        # Expected price in SOL: 100 / 200,000,000 = 0.0000005 SOL
        self.assertAlmostEqual(res["price_quote"], 0.0000005)
        # In USD: 0.0000005 * 200 = $0.0001
        self.assertAlmostEqual(res["price_usd"], 0.0001)
        # Expected market cap: $0.0001 * 1,000,000,000 = $100,000
        self.assertAlmostEqual(res["market_cap_usd"], 100000.0)

    def test_normalize_dex_pair_usdc(self):
        pair_data = {
            "pairAddress": "PairUSDC123",
            "baseToken": {"address": "TokenMint123"},
            "quoteToken": {"address": USDC_MINT, "symbol": "USDC"},
            "priceNative": "0.025",
            "priceUsd": "0.025",
            "marketCap": 25000.0,
        }
        norm = normalize_dex_pair(pair_data)
        self.assertTrue(norm["isUsdcQuoted"])
        self.assertEqual(norm["quoteSymbol"], "USDC")
        self.assertEqual(norm["marketCapUsd"], 25000.0)

    def test_zero_reserves_rejection(self):
        res = calculate_marketcap(0, 0, 1000)
        self.assertFalse(res["valid"])
        self.assertEqual(res["market_cap_usd"], 0.0)


if __name__ == "__main__":
    unittest.main()
