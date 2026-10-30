"""
Multi-Currency Market Cap Resolver for Solana & DEX Analytics Tools.
Fixes USDC/USDT quoted pair market cap over-inflation.
"""

from dataclasses import dataclass
from typing import Optional, Set


class StablecoinRegistry:
    """Registry of known stablecoin mint addresses and ticker symbols on Solana."""

    # Well-known SPL token mints
    STABLECOIN_MINTS: Set[str] = {
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
        "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
        "USDH1SM1ojcxkgZsqgGaNZKoCcR64DGakTypWtHxnsm",  # USDH
        "2b1kV6ydDS3TCgTg5qUsob6BhbcvE4HevXSdHnT8pump",  # PYUSD
    }

    # Common stablecoin ticker symbols
    STABLECOIN_SYMBOLS: Set[str] = {
        "USDC",
        "USDT",
        "USD",
        "PYUSD",
        "USDH",
        "DAI",
        "CASH",
        "EURC",
    }

    @classmethod
    def is_stablecoin(cls, asset_identifier: Optional[str]) -> bool:
        """Determines whether a token mint address or ticker denotes a stablecoin."""
        if not asset_identifier:
            return False
        clean = asset_identifier.strip()
        if clean in cls.STABLECOIN_MINTS:
            return True
        return clean.upper() in cls.STABLECOIN_SYMBOLS


@dataclass(frozen=True)
class MarketCapReport:
    """Structured valuation report for a token pair."""
    price_usd: float
    market_cap_usd: float
    quote_asset: str
    quote_is_stablecoin: bool
    effective_multiplier: float


def derive_token_market_cap(
    supply: float,
    quote_price: float,
    quote_asset: str = "USDC",
    sol_price_usd: float = 1.0,
) -> MarketCapReport:
    """
    Derives USD price and market capitalization for a token.
    Accurately handles USDC/USDT quotes without erroneously scaling by SOL price.

    Parameters:
        supply: Total circulating token supply (must be >= 0).
        quote_price: Execution price per token in units of the quote asset (must be >= 0).
        quote_asset: Symbol or mint address of the quote currency.
        sol_price_usd: Current price of native SOL in USD.

    Returns:
        MarketCapReport containing normalized price and market cap.

    Raises:
        ValueError: If supply or quote_price are negative numbers.
    """
    if supply < 0:
        raise ValueError("Token supply cannot be negative")
    if quote_price < 0:
        raise ValueError("Token quote price cannot be negative")

    is_stable = StablecoinRegistry.is_stablecoin(quote_asset)

    if is_stable:
        # Quote price is already USD denominated
        effective_multiplier = 1.0
    else:
        # Quote price is in native SOL / WSOL; scale by current SOL price
        effective_multiplier = max(0.0, sol_price_usd)

    price_usd = quote_price * effective_multiplier
    market_cap_usd = price_usd * supply

    return MarketCapReport(
        price_usd=price_usd,
        market_cap_usd=market_cap_usd,
        quote_asset=quote_asset,
        quote_is_stablecoin=is_stable,
        effective_multiplier=effective_multiplier,
    )
