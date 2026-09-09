"""Pytest test suite validating flash loan fee calculation invariants for Issue #1303."""

import pytest
from packages.flash_loan_vault import (
    FlashLoanFeeCalculator,
    FlashLoanVaultModel,
    FlashLoanFormalVerifier,
)


def test_fee_rounds_up_when_remainder_exists():
    """Validates that fee calculation with upward rounding produces ceil."""
    amount = 1999
    fee_rate_bps = 5
    precision = 10_000

    truncated_fee = FlashLoanFeeCalculator.calculate_truncated(amount, fee_rate_bps, precision)
    upward_fee = FlashLoanFeeCalculator.calculate_upward(amount, fee_rate_bps, precision)

    assert truncated_fee == 0
    assert upward_fee == 1
    assert upward_fee > truncated_fee


def test_zero_fee_exploit_prevented_across_range():
    """Validates that all micro-loan amounts below 2000 pay at least 1 unit fee."""
    audit = FlashLoanFeeCalculator.audit_zero_fee_vulnerability(max_amount=1999, fee_rate_bps=5)
    assert audit.exploit_prevented
    assert audit.truncated_zero_count == 1999
    assert audit.upward_zero_count == 0


def test_micro_drainage_simulation():
    """Validates cumulative fee protection across repeated flash loan iterations."""
    iterations = 5000
    micro_amount = 1999
    result = FlashLoanFeeCalculator.simulate_micro_drainage(
        iterations=iterations,
        loan_amount=micro_amount,
        fee_rate_bps=5
    )

    assert result.is_protected
    assert result.truncated_total_fee == 0
    assert result.upward_total_fee == iterations
    assert result.fee_leakage_prevented == iterations


def test_vault_reserve_monotonicity():
    """Validates that flash loan executions monotonically increase vault reserves."""
    vault = FlashLoanVaultModel(initial_reserves=5_000_000, fee_rate_bps=5)
    initial_reserves = vault.reserves

    fee1 = vault.execute_flash_loan(100)
    assert vault.reserves == initial_reserves + fee1
    assert fee1 == 1

    fee2 = vault.execute_flash_loan(100_000)
    assert vault.reserves == initial_reserves + fee1 + fee2
    assert fee2 == 50


def test_vault_rejects_exorbitant_loans():
    """Validates that loan requests exceeding available reserves raise ValueError."""
    vault = FlashLoanVaultModel(initial_reserves=1000)
    with pytest.raises(ValueError, match="exceeds available liquidity"):
        vault.execute_flash_loan(1001)


def test_vault_rejects_zero_or_negative_amounts():
    """Validates that non-positive loan amounts raise ValueError."""
    vault = FlashLoanVaultModel()
    with pytest.raises(ValueError, match="must be positive"):
        vault.get_flash_fee(0)
    with pytest.raises(ValueError, match="must be positive"):
        vault.get_flash_fee(-50)


def test_custom_min_fee_floor():
    """Validates that a configured minimum fee floor is strictly enforced."""
    min_fee = 10
    fee = FlashLoanFeeCalculator.calculate_upward(
        amount=100,
        fee_rate_bps=5,
        precision=10_000,
        min_fee=min_fee
    )
    assert fee == min_fee


def test_formal_verifier_suite():
    """Validates that all formal mathematical invariants pass verification."""
    report = FlashLoanFormalVerifier.run_all_verifications()
    assert report["all_passed"]
    assert report["reserve_monotonicity"]
    assert report["fee_inequality"]
    assert report["zero_fee_defense"]


def test_boundary_values():
    """Validates mathematical identities at precision boundaries."""
    precision = 10_000
    rate = 5

    fee_1999 = FlashLoanFeeCalculator.calculate_upward(1999, rate, precision)
    fee_2000 = FlashLoanFeeCalculator.calculate_upward(2000, rate, precision)
    fee_2001 = FlashLoanFeeCalculator.calculate_upward(2001, rate, precision)

    assert fee_1999 == 1
    assert fee_2000 == 1
    assert fee_2001 == 2
