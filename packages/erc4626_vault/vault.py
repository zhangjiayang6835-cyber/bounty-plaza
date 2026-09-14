"""ERC-4626 Vault mathematical model, state engine, and attack simulation."""

from dataclasses import dataclass
from enum import Enum
import math


class RoundingMode(Enum):
    """Rounding directions compliant with OpenZeppelin ERC-4626 specifications."""
    FLOOR = "floor"
    CEIL = "ceil"


@dataclass(frozen=True)
class DonationAttackScenario:
    """Simulation outcomes for an inflation and donation attack vector."""
    offset: int
    attacker_deposit: int
    donation_amount: int
    victim_deposit: int
    victim_shares: int
    victim_net_loss: int
    attacker_net_loss: int

    @property
    def victim_shares_minted(self) -> int:
        """Returns victim shares minted."""
        return self.victim_shares

    @property
    def is_vulnerable(self) -> bool:
        """Returns true if victim experienced zero shares or severe net loss."""
        return self.victim_shares == 0 or self.victim_net_loss > (self.victim_deposit // 10)


class ReentrancyError(RuntimeError):
    """Exception raised when recursive entry into a protected vault method is attempted."""


class ERC4626Vault:
    """Python simulation of OpenZeppelin ERC-4626 Vault with virtual shares offset."""

    def __init__(self, asset_decimals: int = 18, decimals_offset: int = 3):
        """Initializes the vault state with asset decimals and virtual share offset.

        Args:
            asset_decimals: Underlying asset token decimal precision.
            decimals_offset: Offset factor determining virtual shares (10 ** offset).
        """
        self._asset_decimals = asset_decimals
        self._decimals_offset = decimals_offset
        self._total_assets = 0
        self._total_supply = 0
        self._balances: dict[str, int] = {}
        self._locked = False

    @property
    def asset_decimals(self) -> int:
        """Returns underlying asset decimals."""
        return self._asset_decimals

    @property
    def decimals_offset(self) -> int:
        """Returns virtual shares decimal offset."""
        return self._decimals_offset

    @property
    def decimals(self) -> int:
        """Returns vault share decimals including offset."""
        return self._asset_decimals + self._decimals_offset

    @property
    def total_assets(self) -> int:
        """Returns total managed underlying assets."""
        return self._total_assets

    @property
    def total_supply(self) -> int:
        """Returns total minted share tokens."""
        return self._total_supply

    def balance_of(self, account: str) -> int:
        """Returns share token balance of specified account."""
        return self._balances.get(account, 0)

    def _require_non_reentrant(self):
        """Validates that execution context is not already locked."""
        if self._locked:
            raise ReentrancyError("ReentrancyGuard: reentrant call")

    def _mul_div(self, x: int, y: int, denominator: int, rounding: RoundingMode) -> int:
        """Computes floor or ceil division for integer fractions.

        Args:
            x: First numerator factor.
            y: Second numerator factor.
            denominator: Division denominator.
            rounding: Desired rounding mode.

        Returns:
            Computed integer result.
        """
        if denominator == 0:
            raise ZeroDivisionError("Division by zero in vault arithmetic")
        numerator = x * y
        if rounding == RoundingMode.FLOOR:
            return numerator // denominator
        return math.ceil(numerator / denominator)

    def convert_to_shares(self, assets: int, rounding: RoundingMode = RoundingMode.FLOOR) -> int:
        """Converts underlying assets to share amount using virtual shares offset.

        Args:
            assets: Amount of underlying assets.
            rounding: Rounding direction.

        Returns:
            Calculated shares.
        """
        virtual_shares = 10 ** self._decimals_offset
        virtual_assets = 1
        return self._mul_div(
            assets,
            self._total_supply + virtual_shares,
            self._total_assets + virtual_assets,
            rounding,
        )

    def convert_to_assets(self, shares: int, rounding: RoundingMode = RoundingMode.FLOOR) -> int:
        """Converts vault shares to underlying assets using virtual shares offset.

        Args:
            shares: Amount of vault shares.
            rounding: Rounding direction.

        Returns:
            Calculated assets.
        """
        virtual_shares = 10 ** self._decimals_offset
        virtual_assets = 1
        return self._mul_div(
            shares,
            self._total_assets + virtual_assets,
            self._total_supply + virtual_shares,
            rounding,
        )

    def preview_deposit(self, assets: int) -> int:
        """Simulates shares returned for asset deposit rounded down."""
        return self.convert_to_shares(assets, RoundingMode.FLOOR)

    def preview_mint(self, shares: int) -> int:
        """Simulates assets required to mint specified shares rounded up."""
        return self.convert_to_assets(shares, RoundingMode.CEIL)

    def preview_withdraw(self, assets: int) -> int:
        """Simulates shares burned for asset withdrawal rounded up."""
        return self.convert_to_shares(assets, RoundingMode.CEIL)

    def preview_redeem(self, shares: int) -> int:
        """Simulates assets returned for share redemption rounded down."""
        return self.convert_to_assets(shares, RoundingMode.FLOOR)

    def deposit(self, assets: int, receiver: str) -> int:
        """Deposits assets and mints proportional shares to receiver with reentrancy protection.

        Args:
            assets: Underlying asset amount to deposit.
            receiver: Account address receiving minted shares.

        Returns:
            Shares minted.
        """
        self._require_non_reentrant()
        self._locked = True
        try:
            shares = self.preview_deposit(assets)
            if shares == 0:
                raise ValueError("Deposit resulted in zero shares")
            self._total_assets += assets
            self._total_supply += shares
            self._balances[receiver] = self._balances.get(receiver, 0) + shares
            return shares
        finally:
            self._locked = False

    def mint(self, shares: int, receiver: str) -> int:
        """Mints exact shares by depositing required assets with reentrancy protection.

        Args:
            shares: Vault shares to mint.
            receiver: Account address receiving minted shares.

        Returns:
            Assets deposited.
        """
        self._require_non_reentrant()
        self._locked = True
        try:
            assets = self.preview_mint(shares)
            self._total_assets += assets
            self._total_supply += shares
            self._balances[receiver] = self._balances.get(receiver, 0) + shares
            return assets
        finally:
            self._locked = False

    def withdraw(self, assets: int, receiver: str, owner: str) -> int:
        """Withdraws exact assets and burns proportional shares with reentrancy protection.

        Args:
            assets: Asset amount to withdraw.
            receiver: Destination address for withdrawn assets.
            owner: Address owning the shares to burn.

        Returns:
            Shares burned.
        """
        self._require_non_reentrant()
        self._locked = True
        try:
            if not receiver:
                raise ValueError("Invalid receiver address")
            shares = self.preview_withdraw(assets)
            owner_balance = self.balance_of(owner)
            if owner_balance < shares:
                raise ValueError("Insufficient share balance for withdrawal")
            self._balances[owner] = owner_balance - shares
            self._total_supply -= shares
            self._total_assets -= assets
            return shares
        finally:
            self._locked = False

    def redeem(self, shares: int, receiver: str, owner: str) -> int:
        """Redeems shares for proportional assets with reentrancy protection.

        Args:
            shares: Share amount to redeem.
            receiver: Destination address for redeemed assets.
            owner: Address owning the shares to burn.

        Returns:
            Assets returned.
        """
        self._require_non_reentrant()
        self._locked = True
        try:
            if not receiver:
                raise ValueError("Invalid receiver address")
            owner_balance = self.balance_of(owner)
            if owner_balance < shares:
                raise ValueError("Insufficient share balance for redemption")
            assets = self.preview_redeem(shares)
            self._balances[owner] = owner_balance - shares
            self._total_supply -= shares
            self._total_assets -= assets
            return assets
        finally:
            self._locked = False

    def direct_donate(self, assets: int):
        """Simulates external direct asset transfer to the vault without minting shares.

        Args:
            assets: Donated asset amount.
        """
        self._total_assets += assets


def _run_attack_scenario(
    offset: int,
    attacker_deposit: int,
    donation_amount: int,
    victim_deposit: int,
) -> DonationAttackScenario:
    """Simulates attack sequence for a specific decimals offset configuration.

    Args:
        offset: Virtual shares decimals offset.
        attacker_deposit: Initial attacker deposit in wei.
        donation_amount: Direct donation transferred by attacker.
        victim_deposit: Victim deposit in wei.

    Returns:
        Evaluated scenario results.
    """
    vault = ERC4626Vault(asset_decimals=18, decimals_offset=offset)
    attacker_shares = vault.deposit(attacker_deposit, "attacker")
    vault.direct_donate(donation_amount)

    victim_shares = vault.preview_deposit(victim_deposit)
    if victim_shares > 0:
        vault.deposit(victim_deposit, "victim")
        victim_recovered = vault.redeem(victim_shares, "victim", "victim")
    else:
        vault.direct_donate(victim_deposit)
        victim_recovered = 0

    victim_loss = victim_deposit - victim_recovered
    attacker_recovered = vault.redeem(attacker_shares, "attacker", "attacker")
    total_cost = attacker_deposit + donation_amount
    attacker_loss = total_cost - attacker_recovered

    return DonationAttackScenario(
        offset=offset,
        attacker_deposit=attacker_deposit,
        donation_amount=donation_amount,
        victim_deposit=victim_deposit,
        victim_shares=victim_shares,
        victim_net_loss=victim_loss,
        attacker_net_loss=attacker_loss,
    )


def simulate_attack_comparison(
    attacker_deposit: int = 1,
    donation_amount: int = 10**18,
    victim_deposit: int = 5 * 10**17,
) -> tuple[DonationAttackScenario, DonationAttackScenario]:
    """Simulates the donation attack against vulnerable and defended vaults.

    Args:
        attacker_deposit: Initial attacker deposit amount in wei.
        donation_amount: Direct donation amount transferred by attacker in wei.
        victim_deposit: Subsequent regular deposit amount from victim in wei.

    Returns:
        Tuple containing vulnerable scenario result and defended scenario result.
    """
    vulnerable_res = _run_attack_scenario(
        offset=0,
        attacker_deposit=attacker_deposit,
        donation_amount=donation_amount,
        victim_deposit=victim_deposit,
    )
    defended_res = _run_attack_scenario(
        offset=3,
        attacker_deposit=attacker_deposit,
        donation_amount=donation_amount,
        victim_deposit=victim_deposit,
    )
    return vulnerable_res, defended_res
