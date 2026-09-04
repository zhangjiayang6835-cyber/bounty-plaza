"""Unit test suite demonstrating ERC-777 tokensReceived reentrancy attack and mitigation.
Resolves Issue #60: [BUG] Reentrancy via ERC-777 Callback in Withdraw Function ($180 USD).
"""

import pytest
from scripts.erc777_reentrancy_vault import (
    InsufficientBalanceError,
    ReentrancyError,
    SOLIDITY_SECURE_VAULT_CONTRACT,
    SecureVault,
    VulnerableVault,
)


def test_vulnerable_vault_exploit_reproduction():
    """Demonstrates how the vulnerable vault allows draining funds via reentrant callback."""
    vault = VulnerableVault()
    # Honest victim deposits 500
    vault.deposit("victim", 500.0)
    # Attacker deposits 100
    vault.deposit("attacker", 100.0)

    total_withdrawn_by_attacker = 0.0

    # Attacker contract callback hook simulating ERC-777 tokensReceived
    def malicious_callback():
        nonlocal total_withdrawn_by_attacker
        # If attacker still has positive balance according to state, re-enter withdraw!
        if vault.balances.get("attacker", 0.0) > 0 and total_withdrawn_by_attacker < 300.0:
            total_withdrawn_by_attacker += 100.0
            vault.withdraw("attacker", 100.0, recipient_hook=malicious_callback)

    # Initial legitimate withdraw triggers reentrant loop before balance reduction
    total_withdrawn_by_attacker += 100.0
    vault.withdraw("attacker", 100.0, recipient_hook=malicious_callback)

    # In vulnerable vault, attacker was able to withdraw 300 while having only 100 deposited
    assert total_withdrawn_by_attacker == 300.0
    # Balance underflowed or went negative
    assert vault.balances["attacker"] < 0


def test_secure_vault_blocks_reentrancy_with_guard():
    """Verifies that ReentrancyGuard raises ReentrancyError on attempted reentrant callback."""
    vault = SecureVault()
    vault.deposit("victim", 500.0)
    vault.deposit("attacker", 100.0)

    # Malicious callback tries to re-enter withdraw
    def malicious_callback():
        vault.withdraw("attacker", 100.0)

    with pytest.raises(ReentrancyError) as exc_info:
        vault.withdraw("attacker", 100.0, recipient_hook=malicious_callback)

    assert "ReentrancyGuard: reentrant call blocked" in str(exc_info.value)
    # Since the transaction failed / aborted before state corruption, balance remains secure
    assert vault.guard._locked is False


def test_secure_vault_checks_effects_interactions_order():
    """Verifies that balance is updated BEFORE external interaction is called."""
    vault = SecureVault()
    vault.deposit("user1", 250.0)

    observed_balance_in_hook = None

    def inspection_hook():
        nonlocal observed_balance_in_hook
        # At the time the hook executes, internal balance must ALREADY reflect the deduction
        observed_balance_in_hook = vault.balances["user1"]

    withdrawn = vault.withdraw("user1", 100.0, recipient_hook=inspection_hook)
    assert withdrawn == 100.0
    assert observed_balance_in_hook == 150.0
    assert vault.balances["user1"] == 150.0


def test_secure_vault_insufficient_balance_check():
    """Verifies checks step prevents overdrafting."""
    vault = SecureVault()
    vault.deposit("user1", 50.0)

    with pytest.raises(InsufficientBalanceError):
        vault.withdraw("user1", 100.0)


def test_solidity_contract_code_integrity():
    """Verifies production Solidity contract incorporates OpenZeppelin ReentrancyGuard and CEI."""
    assert "contract SecureERC777Vault is ReentrancyGuard" in SOLIDITY_SECURE_VAULT_CONTRACT
    assert "nonReentrant" in SOLIDITY_SECURE_VAULT_CONTRACT
    assert "balances[msg.sender] = userBalance - amount;" in SOLIDITY_SECURE_VAULT_CONTRACT
    assert "token.send(msg.sender, amount" in SOLIDITY_SECURE_VAULT_CONTRACT
