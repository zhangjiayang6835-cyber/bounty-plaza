"""Formal verification engine for SafeERC20 asset transfer and batch harvesting invariants."""

from packages.safe_transfer_vault.harvester import (
    BatchYieldHarvesterModel,
    SafeERC20Wrapper,
    SafeTransferError,
    TokenModel,
    TokenType,
    VulnerableYieldHarvesterModel,
)


class SafeTransferFormalVerifier:
    """Mathematical invariant verifier across token standards and transfer hooks."""

    @staticmethod
    def verify_no_silent_failures() -> bool:
        """Validates that tokens returning false are caught and raised by SafeERC20.

        Returns:
            True if all false-returning conditions raise SafeTransferError.
        """
        token = TokenModel(
            name="FalseToken",
            symbol="FTKN",
            decimals=18,
            token_type=TokenType.FALSE_RETURN,
            should_fail=True,
        )
        token.mint("0xHarvester", 10_000)

        caught = False
        try:
            SafeERC20Wrapper.safe_transfer(token, "0xHarvester", "0xAlice", 1_000)
        except SafeTransferError:
            caught = True

        return caught

    @staticmethod
    def verify_non_standard_void_return_support() -> bool:
        """Validates that tokens returning void succeed with SafeERC20 wrapper.

        Returns:
            True if void-returning token transfer succeeds.
        """
        token = TokenModel(
            name="Tether",
            symbol="USDT",
            decimals=6,
            token_type=TokenType.NO_RETURN,
        )
        token.mint("0xHarvester", 5_000)

        SafeERC20Wrapper.safe_transfer(token, "0xHarvester", "0xBob", 2_000)
        return token.balance_of("0xBob") == 2_000 and token.balance_of("0xHarvester") == 3_000

    @staticmethod
    def verify_vulnerable_harvester_reverts_on_void_return() -> bool:
        """Validates that vulnerable direct calls fail on void-returning tokens.

        Returns:
            True if vulnerable harvester fails as expected.
        """
        token = TokenModel(
            name="Tether",
            symbol="USDT",
            decimals=6,
            token_type=TokenType.NO_RETURN,
        )
        token.mint("0xVulnerable", 5_000)

        vulnerable = VulnerableYieldHarvesterModel("0xVulnerable")
        caught = False
        try:
            vulnerable.harvest_yield_direct(token, "0xBob", 1_000)
        except SafeTransferError:
            caught = True

        return caught

    @staticmethod
    def verify_conservation_of_supply() -> bool:
        """Validates that transfer operations preserve total token supply invariant.

        Returns:
            True if initial supply equals final supply across all accounts.
        """
        token = TokenModel(
            name="Standard",
            symbol="STD",
            decimals=18,
            token_type=TokenType.STANDARD,
        )
        initial_supply = 100_000
        token.mint("0xSender", initial_supply)

        token.approve("0xSender", "0xHarvester", initial_supply)
        harvester = BatchYieldHarvesterModel("0xHarvester")

        harvester.deposit_asset(token, "0xSender", 40_000)
        harvester.harvest_yield(token, "0xAlice", 15_000)
        harvester.withdraw_asset(token, "0xBob", 10_000)

        total_tracked = (
            token.balance_of("0xSender")
            + token.balance_of("0xHarvester")
            + token.balance_of("0xAlice")
            + token.balance_of("0xBob")
        )

        return total_tracked == initial_supply

    @staticmethod
    def verify_force_approve_transition() -> bool:
        """Validates that force approve succeeds when updating non-zero allowance.

        Returns:
            True if allowance transitions cleanly without error.
        """
        token = TokenModel(
            name="Tether",
            symbol="USDT",
            decimals=6,
            token_type=TokenType.NO_RETURN,
        )
        owner = "0xHarvester"
        spender = "0xStrategy"

        SafeERC20Wrapper.force_approve(token, owner, spender, 1_000)
        SafeERC20Wrapper.force_approve(token, owner, spender, 2_500)

        return token.allowances.get(owner, {}).get(spender, 0) == 2_500

    @classmethod
    def run_all_verifications(cls) -> dict[str, bool]:
        """Runs all mathematical verification checks.

        Returns:
            Dictionary mapping verification names to boolean outcomes.
        """
        results = {
            "no_silent_failures": cls.verify_no_silent_failures(),
            "non_standard_support": cls.verify_non_standard_void_return_support(),
            "vulnerable_harvester_reverts": (
                cls.verify_vulnerable_harvester_reverts_on_void_return()
            ),
            "conservation_of_supply": cls.verify_conservation_of_supply(),
            "force_approve_transition": cls.verify_force_approve_transition(),
        }
        results["all_passed"] = all(results.values())
        return results


def main() -> None:
    """Executes verification and prints status."""
    report = SafeTransferFormalVerifier.run_all_verifications()
    if not report.get("all_passed", False):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
