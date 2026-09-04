"""ERC-777 Reentrancy Vulnerable Vault and Secure Vault with Checks-Effects-Interactions and ReentrancyGuard.
Resolves Issue #60: [BUG] Reentrancy via ERC-777 Callback in Withdraw Function ($180 USD).
Reference: SWC-107, The DAO Attack, ERC-777 tokensReceived hook specification.
"""

from typing import Dict, Optional, Callable


class ReentrancyError(RuntimeError):
    """Raised when reentrant call is detected by ReentrancyGuard."""
    pass


class InsufficientBalanceError(ValueError):
    """Raised when withdrawal exceeds available balance."""
    pass


class ReentrancyGuard:
    """Standard mutex lock implementing OpenZeppelin ReentrancyGuard pattern."""

    def __init__(self):
        self._locked = False

    def non_reentrant(self, func):
        def wrapper(*args, **kwargs):
            if self._locked:
                raise ReentrancyError("ReentrancyGuard: reentrant call blocked")
            self._locked = True
            try:
                return func(*args, **kwargs)
            finally:
                self._locked = False
        return wrapper


class VulnerableVault:
    """Vulnerable vault implementation susceptible to ERC-777 tokensReceived reentrancy."""

    def __init__(self):
        self.balances: Dict[str, float] = {}

    def deposit(self, user: str, amount: float):
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        self.balances[user] = self.balances.get(user, 0.0) + amount

    def withdraw(self, user: str, amount: float, recipient_hook: Optional[Callable[[], None]] = None):
        """VULNERABLE: Performs external call / transfer before updating balance (Interaction before Effect)."""
        current_bal = self.balances.get(user, 0.0)
        # Check
        if current_bal < amount:
            raise InsufficientBalanceError("Insufficient balance")

        # Interaction before Effect (SWC-107)
        if recipient_hook:
            # Simulate ERC-777 tokensReceived() hook triggering callback to withdraw
            recipient_hook()

        # Effect (Too late!)
        self.balances[user] = self.balances[user] - amount
        return amount


class SecureVault:
    """Hardened vault using Checks-Effects-Interactions pattern AND ReentrancyGuard."""

    def __init__(self):
        self.balances: Dict[str, float] = {}
        self.guard = ReentrancyGuard()

    def deposit(self, user: str, amount: float):
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        self.balances[user] = self.balances.get(user, 0.0) + amount

    def withdraw(self, user: str, amount: float, recipient_hook: Optional[Callable[[], None]] = None):
        """SECURE:
        1. Guarded with ReentrancyGuard mutex lock.
        2. Strictly adheres to Checks-Effects-Interactions (CEI) pattern.
        """
        if self.guard._locked:
            raise ReentrancyError("ReentrancyGuard: reentrant call blocked")

        self.guard._locked = True
        try:
            # 1. CHECKS
            if amount <= 0:
                raise ValueError("Withdraw amount must be positive")
            current_bal = self.balances.get(user, 0.0)
            if current_bal < amount:
                raise InsufficientBalanceError("Insufficient balance")

            # 2. EFFECTS (State updated BEFORE external interaction)
            self.balances[user] = current_bal - amount

            # 3. INTERACTIONS (External call occurs only after internal state mutation is finalized)
            if recipient_hook:
                recipient_hook()

            return amount
        finally:
            self.guard._locked = False


SOLIDITY_SECURE_VAULT_CONTRACT = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC777/IERC777Recipient.sol";
import "@openzeppelin/contracts/token/ERC777/IERC777.sol";

/**
 * @title SecureERC777Vault
 * @notice Vault protected against ERC-777 tokensReceived hook reentrancy attacks.
 * Resolves Issue #60 (SWC-107).
 */
contract SecureERC777Vault is ReentrancyGuard {
    IERC777 public immutable token;
    mapping(address => uint256) public balances;

    event Deposited(address indexed user, uint256 amount);
    event Withdrawn(address indexed user, uint256 amount);

    constructor(IERC777 _token) {
        token = _token;
    }

    function deposit(uint256 amount) external nonReentrant {
        require(amount > 0, "Deposit amount must be greater than zero");
        token.operatorSend(msg.sender, address(this), amount, "", "");
        balances[msg.sender] += amount;
        emit Deposited(msg.sender, amount);
    }

    /**
     * @notice Withdraw tokens safely.
     * Uses Checks-Effects-Interactions (CEI) AND ReentrancyGuard to prevent
     * exploitation via tokensReceived callback.
     */
    function withdraw(uint256 amount) external nonReentrant {
        // 1. CHECKS
        require(amount > 0, "Withdraw amount must be greater than zero");
        uint256 userBalance = balances[msg.sender];
        require(userBalance >= amount, "Insufficient balance");

        // 2. EFFECTS (Update balance before transfer)
        balances[msg.sender] = userBalance - amount;

        // 3. INTERACTIONS (External token transfer)
        token.send(msg.sender, amount, "");

        emit Withdrawn(msg.sender, amount);
    }
}
"""
