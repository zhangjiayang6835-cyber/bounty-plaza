"""Formal invariant verification engine for flash loan fee calculations."""

from typing import Dict, Any
from .calculator import (
    FlashLoanFeeCalculator,
    FlashLoanVaultModel,
    RoundingMode,
)


class FlashLoanFormalVerifier:
    """Mathematical and state invariant verifier for flash loan implementations."""

    @staticmethod
    def verify_reserve_monotonicity(
        initial_reserves: int = 1_000_000,
        loan_amounts: list[int] | None = None
    ) -> bool:
        """Verifies that flash loan execution strictly increases or preserves reserves.

        Args:
            initial_reserves: Initial liquidity tokens in vault.
            loan_amounts: List of sequential loan amounts to test.

        Returns:
            True if vault reserves monotonically increase.
        """
        if loan_amounts is None:
            loan_amounts = [100, 500, 1999, 10_000, 50_000]

        vault = FlashLoanVaultModel(initial_reserves=initial_reserves)
        last_reserve = vault.reserves

        for amount in loan_amounts:
            vault.execute_flash_loan(amount, RoundingMode.UP)
            current_reserve = vault.reserves
            if current_reserve <= last_reserve:
                return False
            last_reserve = current_reserve

        return True

    @staticmethod
    def verify_fee_inequality(amount: int, fee_rate_bps: int = 5) -> bool:
        """Verifies that ceil fee is always greater than or equal to floor fee.

        Args:
            amount: Loan amount.
            fee_rate_bps: Fee rate in basis points.

        Returns:
            True if ceil fee >= floor fee.
        """
        floor_fee = FlashLoanFeeCalculator.calculate_truncated(amount, fee_rate_bps)
        ceil_fee = FlashLoanFeeCalculator.calculate_upward(amount, fee_rate_bps)
        return ceil_fee >= floor_fee

    @staticmethod
    def verify_zero_fee_defense(max_amount: int = 1999, fee_rate_bps: int = 5) -> bool:
        """Verifies that no positive loan amount yields a zero fee under upward rounding.

        Args:
            max_amount: Upper bound for tested amounts.
            fee_rate_bps: Fee rate in basis points.

        Returns:
            True if all tested positive amounts yield a fee >= 1.
        """
        for amt in range(1, max_amount + 1):
            fee = FlashLoanFeeCalculator.calculate_upward(amt, fee_rate_bps)
            if fee < 1:
                return False
        return True

    @classmethod
    def run_all_verifications(cls) -> Dict[str, Any]:
        """Executes all formal mathematical invariant checks.

        Returns:
            Dictionary containing verification status flags.
        """
        monotonicity = cls.verify_reserve_monotonicity()
        inequality = all(cls.verify_fee_inequality(a) for a in [1, 10, 100, 1999, 5000, 10000])
        zero_defense = cls.verify_zero_fee_defense()

        all_passed = monotonicity and inequality and zero_defense

        return {
            "reserve_monotonicity": monotonicity,
            "fee_inequality": inequality,
            "zero_fee_defense": zero_defense,
            "all_passed": all_passed,
        }
