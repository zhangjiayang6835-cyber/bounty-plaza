"""
Test Suite for Bounty #4107:
USDC-quoted pairs not having the correct marketcap displayed in tools
"""

import pytest
from solutions.usdc_marketcap_resolver import (
    derive_token_market_cap,
    MarketCapReport,
    StablecoinRegistry,
)


def test_usdc_quoted_pair_marketcap_not_multiplied_by_sol():
    """
    Core bug reproduction:
    In USDC-quoted pairs, price is already in USD (USDC).
    It must NOT be multiplied by sol_price_usd.
    """
    supply = 1_000_000.0
    quote_price = 0.50  # 0.50 USDC per token
    quote_asset = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC mint
    sol_price_usd = 185.0

    report = derive_token_market_cap(
        supply=supply,
        quote_price=quote_price,
        quote_asset=quote_asset,
        sol_price_usd=sol_price_usd,
    )

    # Expected: 0.50 * 1,000,000 = $500,000 USD
    # Buggy output was: 0.50 * 1,000,000 * 185 = $92,500,000 USD
    assert report.price_usd == 0.50
    assert report.market_cap_usd == 500_000.0
    assert report.quote_is_stablecoin is True
    assert report.effective_multiplier == 1.0


def test_sol_quoted_pair_correctly_scaled():
    """
    Validates that SOL/WSOL-quoted pairs still multiply by sol_price_usd.
    """
    supply = 1_000_000.0
    quote_price = 0.005  # 0.005 SOL per token
    quote_asset = "So11111111111111111111111111111111111111112"  # WSOL mint
    sol_price_usd = 200.0

    report = derive_token_market_cap(
        supply=supply,
        quote_price=quote_price,
        quote_asset=quote_asset,
        sol_price_usd=sol_price_usd,
    )

    # Expected: 0.005 * 200 = $1.00 USD; 1,000,000 * $1.00 = $1,000,000 USD
    assert report.price_usd == 1.0
    assert report.market_cap_usd == 1_000_000.0
    assert report.quote_is_stablecoin is False
    assert report.effective_multiplier == 200.0


def test_symbol_string_and_usdt_recognition():
    """
    Validates recognition by symbol names ('USDC', 'USDT', 'PYUSD') and USDT mint.
    """
    usdt_mint = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
    assert StablecoinRegistry.is_stablecoin(usdt_mint) is True
    assert StablecoinRegistry.is_stablecoin("USDC") is True
    assert StablecoinRegistry.is_stablecoin("usdt") is True
    assert StablecoinRegistry.is_stablecoin("PYUSD") is True
    assert StablecoinRegistry.is_stablecoin("SOL") is False


def test_boundary_and_invalid_inputs():
    """
    Validates boundary conditions: 0 supply, None price, negative values.
    """
    with pytest.raises(ValueError):
        derive_token_market_cap(supply=-100, quote_price=1.0, quote_asset="USDC")

    with pytest.raises(ValueError):
        derive_token_market_cap(supply=1000, quote_price=-0.5, quote_asset="USDC")

    zero_mcap = derive_token_market_cap(supply=0, quote_price=10.0, quote_asset="USDC")
    assert zero_mcap.market_cap_usd == 0.0
