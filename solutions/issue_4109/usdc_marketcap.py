"""USDC-Quoted Pairs Market Cap & Valuation Normalizer.

Resolves Issue #4109 (and #4107 / blake-guthrie/GLASS#1):
USDC-quoted pairs not having the correct marketcap displayed in tools.
"""

from typing import Any, Dict, Optional

USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
WSOL_MINT = "So11111111111111111111111111111111111111112"
USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"

KNOWN_DECIMALS: Dict[str, int] = {
    USDC_MINT: 6,
    USDT_MINT: 6,
    WSOL_MINT: 9,
    "USDC": 6,
    "USDT": 6,
    "WSOL": 9,
    "SOL": 9,
}


def get_quote_decimals(quote_mint_or_symbol: str) -> int:
    """Return standard token decimals for known quote mints."""
    return KNOWN_DECIMALS.get(quote_mint_or_symbol, 9)


def get_quote_to_usd_rate(quote_mint_or_symbol: str, sol_price_usd: Optional[float] = None) -> Optional[float]:
    """Calculate the conversion rate from quote currency units to USD."""
    if quote_mint_or_symbol in (USDC_MINT, USDT_MINT, "USDC", "USDT"):
        return 1.0
    if quote_mint_or_symbol in (WSOL_MINT, "WSOL", "SOL"):
        return sol_price_usd if sol_price_usd is not None else None
    return None


def calculate_marketcap(
    base_reserve_raw: int,
    quote_reserve_raw: int,
    total_supply_raw: int,
    quote_mint_or_symbol: str = USDC_MINT,
    base_decimals: int = 6,
    quote_decimals: Optional[int] = None,
    sol_price_usd: Optional[float] = None,
) -> Dict[str, Any]:
    """Calculate price and market capitalization for a token pair.

    Correctly scales reserve decimals when quote is USDC (6 decimals)
    versus WSOL (9 decimals) and eliminates mistaken SOL multiplication
    on USD-pegged quote pairs.
    """
    if base_reserve_raw <= 0 or quote_reserve_raw <= 0 or total_supply_raw <= 0:
        return {
            "price_quote": 0.0,
            "price_usd": 0.0,
            "market_cap_usd": 0.0,
            "is_usdc_quoted": quote_mint_or_symbol in (USDC_MINT, "USDC"),
            "valid": False,
        }

    q_dec = quote_decimals if quote_decimals is not None else get_quote_decimals(quote_mint_or_symbol)
    base_scale = 10 ** base_decimals
    quote_scale = 10 ** q_dec

    base_reserve = base_reserve_raw / base_scale
    quote_reserve = quote_reserve_raw / quote_scale
    total_supply = total_supply_raw / base_scale

    price_quote = quote_reserve / base_reserve
    usd_rate = get_quote_to_usd_rate(quote_mint_or_symbol, sol_price_usd=sol_price_usd)

    if usd_rate is not None:
        price_usd = price_quote * usd_rate
        market_cap_usd = price_usd * total_supply
    else:
        price_usd = 0.0
        market_cap_usd = 0.0

    return {
        "price_quote": price_quote,
        "price_usd": price_usd,
        "market_cap_usd": market_cap_usd,
        "quote_symbol": "USDC" if quote_mint_or_symbol in (USDC_MINT, "USDC") else "SOL",
        "is_usdc_quoted": quote_mint_or_symbol in (USDC_MINT, "USDC"),
        "valid": True,
    }


def normalize_dex_pair(pair_data: dict, sol_price_usd: Optional[float] = None) -> dict:
    """Normalize DEX pair structure to ensure accurate marketcap on USDC pairs."""
    quote_token = pair_data.get("quoteToken", {})
    quote_mint = quote_token.get("address", "")
    quote_symbol = quote_token.get("symbol", "")

    is_usdc = quote_mint == USDC_MINT or quote_symbol == "USDC"
    price_native = float(pair_data.get("priceNative", 0.0) or 0.0)
    price_usd = float(pair_data.get("priceUsd", 0.0) or 0.0)

    # When priceUsd is missing on a USDC pair, priceNative IS the USD price
    if is_usdc and price_usd == 0.0 and price_native > 0.0:
        price_usd = price_native

    market_cap = pair_data.get("marketCap")
    fdv = pair_data.get("fdv")

    if market_cap is None and fdv is not None:
        market_cap = fdv

    return {
        "pairAddress": pair_data.get("pairAddress"),
        "baseMint": pair_data.get("baseToken", {}).get("address"),
        "quoteMint": quote_mint,
        "quoteSymbol": "USDC" if is_usdc else quote_symbol,
        "isUsdcQuoted": is_usdc,
        "priceNative": price_native,
        "priceUsd": price_usd,
        "marketCapUsd": market_cap if market_cap is not None else 0.0,
    }
