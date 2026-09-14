"""SafeERC20 asset transfer and batch yield harvesting simulation module."""

from dataclasses import dataclass, field
from enum import Enum


class TokenType(Enum):
    """Enumeration of simulated ERC-20 token interface behaviors."""
    STANDARD = "standard"
    NO_RETURN = "no_return"
    FALSE_RETURN = "false_return"
    REVERTING = "reverting"


class SafeTransferError(Exception):
    """Exception raised when an asset transfer fails or returns invalid status."""


@dataclass
class TokenModel:
    """Mathematical simulation model of an ERC-20 token contract.

    Attributes:
        name: Human-readable token name.
        symbol: Short token ticker symbol.
        decimals: Decimal precision of the token.
        token_type: Interface behavior classification.
        balances: Mapping from account address to unit balance.
        allowances: Mapping from owner to spender allowance units.
        should_fail: Flag forcing false return for testing.
    """
    name: str
    symbol: str
    decimals: int
    token_type: TokenType
    balances: dict[str, int] = field(default_factory=dict)
    allowances: dict[str, dict[str, int]] = field(default_factory=dict)
    should_fail: bool = False

    def mint(self, recipient: str, amount: int) -> None:
        """Mints units to destination account.

        Args:
            recipient: Destination account address.
            amount: Units of token to mint.
        """
        if amount <= 0:
            raise ValueError("Mint amount must be positive")
        current = self.balances.get(recipient, 0)
        self.balances[recipient] = current + amount

    def balance_of(self, account: str) -> int:
        """Queries unit balance of specified account.

        Args:
            account: Target account address.

        Returns:
            Current balance in token units.
        """
        return self.balances.get(account, 0)

    def transfer(self, sender: str, recipient: str, amount: int) -> bool | None:
        """Simulates low-level transfer execution.

        Args:
            sender: Source account address.
            recipient: Destination account address.
            amount: Units to transfer.

        Returns:
            Boolean status for standard tokens, None for void return tokens.

        Raises:
            SafeTransferError: If token reverts on transfer.
        """
        if self.token_type == TokenType.REVERTING:
            raise SafeTransferError(f"{self.symbol}: transfer reverted")

        if self.token_type == TokenType.FALSE_RETURN and self.should_fail:
            return False

        sender_bal = self.balances.get(sender, 0)
        if sender_bal < amount:
            if self.token_type == TokenType.FALSE_RETURN:
                return False
            raise SafeTransferError(f"{self.symbol}: insufficient balance")

        self.balances[sender] = sender_bal - amount
        self.balances[recipient] = self.balances.get(recipient, 0) + amount

        if self.token_type == TokenType.NO_RETURN:
            return None
        return True

    def transfer_from(
        self,
        spender: str,
        owner: str,
        recipient: str,
        amount: int
    ) -> bool | None:
        """Simulates low-level transferFrom execution.

        Args:
            spender: Caller executing transfer.
            owner: Source account address.
            recipient: Destination account address.
            amount: Units to transfer.

        Returns:
            Boolean status for standard tokens, None for void return tokens.

        Raises:
            SafeTransferError: If transfer reverts.
        """
        if self.token_type == TokenType.REVERTING:
            raise SafeTransferError(f"{self.symbol}: transferFrom reverted")

        if self.token_type == TokenType.FALSE_RETURN and self.should_fail:
            return False

        allowed = self.allowances.get(owner, {}).get(spender, 0)
        if allowed < amount:
            if self.token_type == TokenType.FALSE_RETURN:
                return False
            raise SafeTransferError(f"{self.symbol}: insufficient allowance")

        owner_bal = self.balances.get(owner, 0)
        if owner_bal < amount:
            if self.token_type == TokenType.FALSE_RETURN:
                return False
            raise SafeTransferError(f"{self.symbol}: insufficient balance")

        self.allowances[owner][spender] = allowed - amount
        self.balances[owner] = owner_bal - amount
        self.balances[recipient] = self.balances.get(recipient, 0) + amount

        if self.token_type == TokenType.NO_RETURN:
            return None
        return True

    def approve(self, owner: str, spender: str, amount: int) -> bool | None:
        """Simulates allowance approval.

        Args:
            owner: Token owner granting allowance.
            spender: Authorized spender address.
            amount: Allowance units.

        Returns:
            Boolean status or None for void return.

        Raises:
            SafeTransferError: If non-zero to non-zero without reset.
        """
        if owner not in self.allowances:
            self.allowances[owner] = {}

        current = self.allowances[owner].get(spender, 0)
        if self.token_type == TokenType.NO_RETURN:
            if amount != 0 and current != 0:
                raise SafeTransferError("USDT: approve non-zero to non-zero disallowed")

        self.allowances[owner][spender] = amount
        if self.token_type == TokenType.NO_RETURN:
            return None
        return True


class SafeERC20Wrapper:
    """SafeERC20 wrapper protecting against non-standard ERC-20 return behaviors."""

    @staticmethod
    def safe_transfer(token: TokenModel, sender: str, recipient: str, amount: int) -> None:
        """Executes safe transfer, validating boolean return and void returns.

        Args:
            token: Target token model.
            sender: Source account.
            recipient: Destination account.
            amount: Units to transfer.

        Raises:
            SafeTransferError: If transfer fails or returns false.
        """
        if not recipient:
            raise SafeTransferError("SafeERC20: zero address recipient")
        if amount == 0:
            raise SafeTransferError("SafeERC20: zero amount transfer")

        result = token.transfer(sender, recipient, amount)
        if result is False:
            raise SafeTransferError(f"SafeERC20FailedOperation: {token.symbol}")

    @staticmethod
    def safe_transfer_from(
        token: TokenModel,
        spender: str,
        owner: str,
        recipient: str,
        amount: int
    ) -> None:
        """Executes safe transferFrom, enforcing non-false return data.

        Args:
            token: Target token model.
            spender: Authorized caller.
            owner: Source account.
            recipient: Destination account.
            amount: Units to transfer.

        Raises:
            SafeTransferError: If transferFrom fails or returns false.
        """
        if not recipient:
            raise SafeTransferError("SafeERC20: zero address recipient")
        if amount == 0:
            raise SafeTransferError("SafeERC20: zero amount transfer")

        result = token.transfer_from(spender, owner, recipient, amount)
        if result is False:
            raise SafeTransferError(f"SafeERC20FailedOperation: {token.symbol}")

    @staticmethod
    def force_approve(token: TokenModel, owner: str, spender: str, amount: int) -> None:
        """Approves allowance, resetting to zero first if required by token standard.

        Args:
            token: Target token model.
            owner: Approving account.
            spender: Authorized spender.
            amount: Target allowance.
        """
        try:
            res = token.approve(owner, spender, amount)
            if res is False:
                raise SafeTransferError(f"SafeERC20: approve returned false for {token.symbol}")
        except SafeTransferError:
            token.approve(owner, spender, 0)
            token.approve(owner, spender, amount)


class BatchYieldHarvesterModel:
    """Simulation of production BatchYieldHarvester contract using SafeERC20."""

    def __init__(self, address: str = "0xHarvester"):
        """Initializes harvester model with an address identifier.

        Args:
            address: Mock contract address.
        """
        self.address = address

    def deposit_asset(self, token: TokenModel, sender: str, amount: int) -> None:
        """Deposits asset from sender into harvester via SafeERC20.

        Args:
            token: Target token contract.
            sender: Depositor account.
            amount: Units to deposit.
        """
        SafeERC20Wrapper.safe_transfer_from(token, self.address, sender, self.address, amount)

    def harvest_yield(self, token: TokenModel, recipient: str, amount: int) -> None:
        """Harvests yield to a recipient via SafeERC20.

        Args:
            token: Yield token contract.
            recipient: Beneficiary account.
            amount: Units of yield.
        """
        SafeERC20Wrapper.safe_transfer(token, self.address, recipient, amount)

    def batch_harvest_yield(
        self,
        tokens: list[TokenModel],
        recipients: list[str],
        amounts: list[int]
    ) -> int:
        """Executes atomic batch yield distribution across diverse tokens.

        Args:
            tokens: List of token contracts.
            recipients: Beneficiary addresses.
            amounts: Quantity units for each transfer.

        Returns:
            Count of successfully completed transfers.

        Raises:
            ValueError: If array lengths do not match.
        """
        if len(tokens) != len(recipients) or len(recipients) != len(amounts):
            raise ValueError("Array lengths mismatch in batch harvest")

        for token, recipient, amount in zip(tokens, recipients, amounts):
            self.harvest_yield(token, recipient, amount)

        return len(tokens)

    def withdraw_asset(self, token: TokenModel, destination: str, amount: int) -> None:
        """Withdraws protocol asset to destination.

        Args:
            token: Asset token contract.
            destination: Receiving account.
            amount: Units to withdraw.
        """
        SafeERC20Wrapper.safe_transfer(token, self.address, destination, amount)


class VulnerableYieldHarvesterModel:
    """Vulnerable harvester model that makes unchecked direct transfer calls."""

    def __init__(self, address: str = "0xVulnerableHarvester"):
        """Initializes vulnerable harvester model.

        Args:
            address: Mock contract address.
        """
        self.address = address

    def harvest_yield_direct(self, token: TokenModel, recipient: str, amount: int) -> None:
        """Executes direct transfer call expecting boolean return value.

        Args:
            token: Yield token contract.
            recipient: Beneficiary account.
            amount: Units to transfer.

        Raises:
            SafeTransferError: If token does not return boolean True.
        """
        result = token.transfer(self.address, recipient, amount)
        if result is None:
            raise SafeTransferError(f"ABI decoding error: {token.symbol} did not return bool")
        if not result:
            raise SafeTransferError(f"Direct transfer failed for {token.symbol}")

    def batch_harvest_yield_direct(
        self,
        tokens: list[TokenModel],
        recipients: list[str],
        amounts: list[int]
    ) -> int:
        """Executes batch transfer directly, vulnerable to missing boolean returns.

        Args:
            tokens: List of token contracts.
            recipients: Beneficiary addresses.
            amounts: Quantities to transfer.

        Returns:
            Count of transfers executed.
        """
        if len(tokens) != len(recipients) or len(recipients) != len(amounts):
            raise ValueError("Array lengths mismatch in batch harvest")

        for token, recipient, amount in zip(tokens, recipients, amounts):
            self.harvest_yield_direct(token, recipient, amount)

        return len(tokens)


def main() -> None:
    """Self-contained verification demonstration."""
    token = TokenModel(name="Tether", symbol="USDT", decimals=6, token_type=TokenType.NO_RETURN)
    token.mint("0xHarvester", 1_000_000)
    harvester = BatchYieldHarvesterModel("0xHarvester")
    harvester.harvest_yield(token, "0xBob", 500_000)


if __name__ == "__main__":
    main()
