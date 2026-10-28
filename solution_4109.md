# Solution for Issue #4109: USDC-quoted pairs not having the correct marketcap displayed in tools

## Problem Analysis
In multi-quote Solana token tracking tools, liquidity pools are predominantly paired with Wrapped SOL (WSOL, 9 decimals / 1e9). When tools ingest USDC-quoted pools (USDC mint `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`, 6 decimals / 1e6), two distinct bugs frequently manifest:
1. **Decimal Scaling Mismatch**: Tools divide the raw USDC quote reserve by `1e9` (lamports) instead of `1e6`, understating the USD quote reserve and resulting token market cap by a factor of 1,000x.
2. **Quote Unit Misconversion**: Tools erroneously multiply the already-USD-denominated quote amount by the active SOL/USD exchange rate, artificially inflating or distorting the market cap calculation.

## Solution Architecture
1. **Quote Decimals Lookup (`get_quote_decimals`)**:
   - Maps `USDC` / `USDT` to 6 decimals (`1e6`).
   - Maps `WSOL` / `SOL` to 9 decimals (`1e9`).
2. **Deterministic Market Cap Valuation (`calculate_marketcap`)**:
   - Scales `base_reserve = base_reserve_raw / (10 ** base_decimals)`.
   - Scales `quote_reserve = quote_reserve_raw / (10 ** quote_decimals)`.
   - Applies conversion rate `1.0` when quote is USDC or USDT, and `sol_price_usd` when quote is WSOL.
   - Derives `market_cap_usd = price_usd * total_supply`.
3. **DEX Pair Normalization (`normalize_dex_pair`)**:
   - Accurately identifies USDC-quoted pairs and populates `isUsdcQuoted`.
   - Prevents unneeded native-to-USD currency re-multiplication.

## Deliverables
- `solutions/issue_4109/usdc_marketcap.py`: Full valuation logic, decimal scaling, and pair normalization.
- `solutions/issue_4109/test_usdc_marketcap.py`: 6 test cases verifying decimal scaling, market cap accuracy, and pair normalization.

## Cross-References
- Issue #4109: [zhangjiayang6835-cyber/bounty-plaza#4109](https://github.com/zhangjiayang6835-cyber/bounty-plaza/issues/4109)
- Issue #4107: [zhangjiayang6835-cyber/bounty-plaza#4107](https://github.com/zhangjiayang6835-cyber/bounty-plaza/issues/4107)
- Upstream Target: [blake-guthrie/GLASS#1](https://github.com/blake-guthrie/GLASS/issues/1)
