"""Flash loan fee calculation engine and state transition simulation models."""

from dataclasses import dataclass
from enum import Enum
import math


class RoundingMode(Enum):
    """Rounding directions for fee arithmetic."""
    DOWN = "down"
    UP = "up"


@dataclass(frozen=True)
class MicroDrainageResult:
    """Outcomes of repeated flash loan iterations comparing rounding modes."""
    iterations: int
    loan_amount: int
    fee_rate_bps: int
    precision: int
    truncated_total_fee: int
    upward_total_fee: int
    fee_leakage_prevented: int

    @property
    def is_protected(self) -> bool:
        """Returns whether upward rounding successfully prevented micro-drainage."""
        return self.upward_total_fee > self.truncated_total_fee


@dataclass(frozen=True)
class ZeroFeeExploitResult:
    """Outcomes of attempting zero-fee flash loans across small amounts."""
    tested_amounts: int
    truncated_zero_count: int
    upward_zero_count: int
    exploit_prevented: bool


class FlashLoanFeeCalculator:
    """Mathematical fee calculator supporting standard truncation and upward ceiling rounding."""

    FEE_PRECISION: int = 10_000

    @staticmethod
    def calculate_truncated(amount: int, fee_rate_bps: int, precision: int = 10_000) -> int:
        """Calculates fee using naive downward integer truncation.

        Args:
            amount: Principal loan amount.
            fee_rate_bps: Fee rate expressed in basis points.
            precision: Fee rate denominator.

        Returns:
            Calculated fee rounded down toward zero.
        """
        if amount <= 0 or fee_rate_bps <= 0 or precision <= 0:
            return 0
        return (amount * fee_rate_bps) // precision

    @staticmethod
    def calculate_upward(
        amount: int,
        fee_rate_bps: int,
        precision: int = 10_000,
        min_fee: int = 1
    ) -> int:
        """Calculates fee using Math.mulDiv upward ceiling rounding with zero-fee prevention.

        Args:
            amount: Principal loan amount.
            fee_rate_bps: Fee rate expressed in basis points.
            precision: Fee rate denominator.
            min_fee: Minimum non-zero fee threshold.

        Returns:
            Calculated fee rounded up in favor of vault reserves.
        """
        if amount <= 0 or fee_rate_bps <= 0 or precision <= 0:
            return 0
        product = amount * fee_rate_bps
        fee = math.ceil(product / precision)
        fee = max(fee, 1)
        fee = max(fee, min_fee)
        return fee

    @classmethod
    def simulate_micro_drainage(
        cls,
        iterations: int,
        loan_amount: int,
        fee_rate_bps: int = 5,
        precision: int = 10_000
    ) -> MicroDrainageResult:
        """Simulates iterative flash loans under truncation vs upward rounding.

        Args:
            iterations: Number of sequential loans executed.
            loan_amount: Amount borrowed in each iteration.
            fee_rate_bps: Fee rate in basis points.
            precision: Precision denominator.

        Returns:
            MicroDrainageResult containing aggregated metrics.
        """
        trunc_fee_single = cls.calculate_truncated(loan_amount, fee_rate_bps, precision)
        upward_fee_single = cls.calculate_upward(loan_amount, fee_rate_bps, precision)

        trunc_total = trunc_fee_single * iterations
        upward_total = upward_fee_single * iterations
        prevented = upward_total - trunc_total

        return MicroDrainageResult(
            iterations=iterations,
            loan_amount=loan_amount,
            fee_rate_bps=fee_rate_bps,
            precision=precision,
            truncated_total_fee=trunc_total,
            upward_total_fee=upward_total,
            fee_leakage_prevented=prevented,
        )

    @classmethod
    def audit_zero_fee_vulnerability(
        cls,
        max_amount: int = 1999,
        fee_rate_bps: int = 5,
        precision: int = 10_000
    ) -> ZeroFeeExploitResult:
        """Audits a range of micro loan amounts for zero-fee exploitation vulnerability.

        Args:
            max_amount: Upper bound of tested loan amounts.
            fee_rate_bps: Fee rate in basis points.
            precision: Precision denominator.

        Returns:
            ZeroFeeExploitResult detailing zero-fee occurrences.
        """
        tested = 0
        trunc_zeros = 0
        upward_zeros = 0

        for amt in range(1, max_amount + 1):
            tested += 1
            if cls.calculate_truncated(amt, fee_rate_bps, precision) == 0:
                trunc_zeros += 1
            if cls.calculate_upward(amt, fee_rate_bps, precision) == 0:
                upward_zeros += 1

        prevented = (trunc_zeros > 0) and (upward_zeros == 0)
        return ZeroFeeExploitResult(
            tested_amounts=tested,
            truncated_zero_count=trunc_zeros,
            upward_zero_count=upward_zeros,
            exploit_prevented=prevented,
        )


class FlashLoanVaultModel:
    """State machine model simulating flash loan lending and reserve accounting."""

    def __init__(
        self,
        initial_reserves: int = 1_000_000_000_000,
        fee_rate_bps: int = 5,
        min_fee: int = 1
    ):
        """Initializes vault state.

        Args:
            initial_reserves: Initial liquidity tokens held by vault.
            fee_rate_bps: Flash loan fee rate in basis points.
            min_fee: Minimum fee threshold.
        """
        self._reserves: int = initial_reserves
        self._fee_rate_bps: int = fee_rate_bps
        self._min_fee: int = min_fee
        self._total_fees_collected: int = 0
        self._total_loans_issued: int = 0

    @property
    def reserves(self) -> int:
        """Returns current reserve balance."""
        return self._reserves

    @property
    def fee_rate_bps(self) -> int:
        """Returns fee rate in basis points."""
        return self._fee_rate_bps

    @property
    def min_fee(self) -> int:
        """Returns minimum fee floor."""
        return self._min_fee

    @property
    def total_fees_collected(self) -> int:
        """Returns aggregate fees collected."""
        return self._total_fees_collected

    @property
    def total_loans_issued(self) -> int:
        """Returns total count of loans issued."""
        return self._total_loans_issued

    def get_flash_fee(self, amount: int, mode: RoundingMode = RoundingMode.UP) -> int:
        """Computes loan fee for a given amount and rounding direction.

        Args:
            amount: Principal amount to borrow.
            mode: RoundingMode applied.

        Returns:
            Computed fee amount.
        """
        if amount <= 0:
            raise ValueError("Loan amount must be positive")
        if mode == RoundingMode.UP:
            return FlashLoanFeeCalculator.calculate_upward(
                amount, self._fee_rate_bps, FlashLoanFeeCalculator.FEE_PRECISION, self._min_fee
            )
        return FlashLoanFeeCalculator.calculate_truncated(
            amount, self._fee_rate_bps, FlashLoanFeeCalculator.FEE_PRECISION
        )

    def execute_flash_loan(self, amount: int, mode: RoundingMode = RoundingMode.UP) -> int:
        """Executes a flash loan against vault reserves.

        Args:
            amount: Principal loan amount.
            mode: Rounding mode for fee determination.

        Returns:
            Fee collected from borrower.
        """
        if amount > self._reserves:
            raise ValueError("Requested loan exceeds available liquidity")
        fee = self.get_flash_fee(amount, mode)
        self._reserves += fee
        self._total_fees_collected += fee
        self._total_loans_issued += 1
        return fee


def main() -> int:
    """Executes standalone benchmark and verification.

    Returns:
        Status code 0 on success.
    """
    calculator = FlashLoanFeeCalculator()
    sim_result = calculator.simulate_micro_drainage(iterations=1000, loan_amount=1999)
    zero_result = calculator.audit_zero_fee_vulnerability(max_amount=1999)

    if not sim_result.is_protected or not zero_result.exploit_prevented:
        return 1

    vault = FlashLoanVaultModel()
    fee = vault.execute_flash_loan(100_000)
    if fee <= 0:
        return 1

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
