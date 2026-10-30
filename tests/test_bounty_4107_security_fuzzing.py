"""
Security Fuzzing and Numerical Precision Test Suite for Bounty #4107.
Validates CWE-682 (Incorrect Calculation), sub-penny fractional pricing, and extreme bounds.
"""

import pytest
import math
from solutions.usdc_marketcap_resolver import (
    derive_token_market_cap,
    StablecoinRegistry,
)


def test_cwe_682_fractional_sub_penny_pricing():
    """
    CWE-682: Micro-cap tokens often trade at fractions of a cent (e.g., $0.00001234).
    Validates precision without float truncation or catastrophic cancellation.
    """
    supply = 1_000_000_000_000.0  # 1 Trillion tokens
    quote_price = 0.000012345678
    quote_asset = "USDC"
    sol_price_usd = 195.5

    report = derive_token_market_cap(
        supply=supply,
        quote_price=quote_price,
        quote_asset=quote_asset,
        sol_price_usd=sol_price_usd,
    )

    expected_mcap = supply * quote_price
    assert math.isclose(report.price_usd, quote_price, rel_tol=1e-9)
    assert math.isclose(report.market_cap_usd, expected_mcap, rel_tol=1e-9)
    assert report.effective_multiplier == 1.0


def test_extreme_supply_bounds():
    """
    Validates that quadrillion-level supplies do not cause overflow or negative results.
    """
    large_supply = 1e15
    quote_price = 0.00000001
    report = derive_token_market_cap(
        supply=large_supply,
        quote_price=quote_price,
        quote_asset="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    )
    assert report.market_cap_usd == 1e7  # 10 Million USD
    assert report.price_usd == 1e-8


def test_pyusd_and_eurc_recognition():
    """
    Validates that PayPal USD (PYUSD) and Euro Coin (EURC) are handled as stablecoins.
    """
    assert StablecoinRegistry.is_stablecoin("2b1kV6ydDS3TCgTg5qUsob6BhbcvE4HevXSdHnT8pump") is True
    assert StablecoinRegistry.is_stablecoin("EURC") is True

    report_pyusd = derive_token_market_cap(
        supply=500_000,
        quote_price=2.50,
        quote_asset="PYUSD",
        sol_price_usd=150.0,
    )
    assert report_pyusd.price_usd == 2.50
    assert report_pyusd.market_cap_usd == 1_250_000.0
    assert report_pyusd.effective_multiplier == 1.0


def test_zero_sol_price_fallback():
    """
    If SOL price is 0 or negative due to RPC failure, multiplier clamps to 0.
    """
    report = derive_token_market_cap(
        supply=1000,
        quote_price=1.0,
        quote_asset="SOL",
        sol_price_usd=-5.0,
    )
    assert report.effective_multiplier == 0.0
    assert report.market_cap_usd == 0.0
