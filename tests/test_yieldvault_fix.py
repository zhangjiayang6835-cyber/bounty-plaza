"""Tests for the ERC-4626 vault fix (bounty #1304).

Verifies that the fixed vault:
  * neutralizes the first-depositor share-inflation attack (virtual shares /
    offset decimals, OZ ERC-4626 standard),
  * blocks reentrancy on every external deposit/withdraw routine,
while demonstrating that the original vulnerable contract fails both properties.
"""

import pytest

from yieldvault_fix import (
    ERC20,
    FixedYieldVault,
    ReentrantERC20,
    ReentrancyError,
    VulnerableYieldVault,
)

TEN18 = 10 ** 18
MAX = 2 ** 256 - 1


def _fund_and_approve(token, vault, user, amount):
    token.mint(user, amount)
    token.approve(user, vault, MAX)


@pytest.fixture
def token():
    return ERC20()


@pytest.fixture
def vulnerable(token):
    return VulnerableYieldVault(token)


@pytest.fixture
def fixed(token):
    return FixedYieldVault(token)


# ── 1. Share inflation (first-depositor donation attack) ─────────────────────

def test_vulnerable_vault_total_loss_on_inflation_attack(token, vulnerable):
    attacker = "attacker"
    victim = "victim"

    _fund_and_approve(token, vulnerable, attacker, TEN18 + 2)
    shares = vulnerable.deposit(1, attacker, caller=attacker)
    assert shares == 1

    token.transfer(attacker, vulnerable, TEN18)
    assert vulnerable.total_assets() == TEN18 + 1

    _fund_and_approve(token, vulnerable, victim, TEN18)
    victim_shares = vulnerable.deposit(TEN18, victim, caller=victim)
    assert victim_shares == 0

    back = vulnerable.redeem(0, victim, victim, caller=victim)
    assert back == 0


def test_fixed_vault_resists_inflation_attack(token, fixed):
    attacker = "attacker"
    victim = "victim"

    _fund_and_approve(token, fixed, attacker, TEN18 + 2)
    attacker_shares = fixed.deposit(1, attacker, caller=attacker)
    assert attacker_shares == 10 ** 6

    token.transfer(attacker, fixed, TEN18)
    assert fixed.total_assets() == TEN18 + 1

    _fund_and_approve(token, fixed, victim, TEN18)
    victim_shares = fixed.deposit(TEN18, victim, caller=victim)
    assert victim_shares > 0

    back = fixed.redeem(victim_shares, victim, victim, caller=victim)
    assert back > 0


def test_fixed_vault_no_zero_share_rounding_after_donation(token, fixed):
    _fund_and_approve(token, fixed, "a", TEN18 + 1)
    fixed.deposit(1, "a", caller="a")
    token.transfer("a", fixed, TEN18)

    _fund_and_approve(token, fixed, "b", TEN18)
    shares = fixed.deposit(TEN18, "b", caller="b")
    assert shares > 0


# ── 2. Deposit / redeem round trip ───────────────────────────────────────────

def test_fixed_vault_deposit_redeem_round_trip(token, fixed):
    user = "alice"
    _fund_and_approve(token, fixed, user, TEN18)

    shares = fixed.deposit(TEN18, user, caller=user)
    assert shares > 0
    assert fixed.balance_of(user) == shares
    assert fixed.total_supply() == shares
    assert fixed.total_assets() == TEN18

    back = fixed.redeem(shares, user, user, caller=user)
    assert back == TEN18
    assert fixed.total_assets() == 0
    assert fixed.balance_of(user) == 0


def test_fixed_vault_withdraw_redeem_accounting(token, fixed):
    user = "bob"
    _fund_and_approve(token, fixed, user, TEN18)
    fixed.deposit(TEN18, user, caller=user)

    assert fixed.max_redeem(user) == fixed.balance_of(user)
    assert 0 < fixed.max_withdraw(user) <= TEN18

    shares_needed = fixed.preview_withdraw(TEN18)
    assert shares_needed == fixed.balance_of(user)
    out = fixed.withdraw(TEN18, user, user, caller=user)
    assert out == shares_needed
    assert fixed.total_assets() == 0


def test_convert_to_shares_and_assets_consistent(token, fixed):
    _fund_and_approve(token, fixed, "carol", TEN18)
    fixed.deposit(TEN18, "carol", caller="carol")

    back = fixed.convert_to_assets(fixed.convert_to_shares(TEN18))
    assert back > 0
    assert fixed.convert_to_assets(0) == 0
    assert fixed.convert_to_shares(0) == 0


# ── 3. Reentrancy guards ─────────────────────────────────────────────────────

@pytest.fixture
def reentrant_token():
    return ReentrantERC20()


def test_vulnerable_vault_allows_reentrant_deposit(reentrant_token):
    vuln = VulnerableYieldVault(reentrant_token)
    _fund_and_approve(reentrant_token, vuln, "alice", TEN18 * 10)

    fired = {"once": False}

    def hook():
        if not fired["once"]:
            fired["once"] = True
            vuln.deposit(1, "bob", caller="alice")

    reentrant_token.reentrancy_hook = hook
    shares = vuln.deposit(TEN18, "alice", caller="alice")

    assert shares == TEN18
    assert vuln.balance_of("alice") == TEN18
    assert vuln.balance_of("bob") == 1
    assert vuln.total_supply() == TEN18 + 1


def test_fixed_vault_reentrancy_guard_blocks_reentrant_deposit(reentrant_token):
    fixed = FixedYieldVault(reentrant_token)
    _fund_and_approve(reentrant_token, fixed, "alice", TEN18 * 10)

    def hook():
        fixed.deposit(1, "bob", caller="alice")

    reentrant_token.reentrancy_hook = hook

    with pytest.raises(ReentrancyError):
        fixed.deposit(TEN18, "alice", caller="alice")

    assert fixed.total_supply() == 0
    assert fixed.total_assets() == 0
    assert fixed.balance_of("bob") == 0


def test_fixed_vault_reentrancy_guard_blocks_reentrant_withdraw(reentrant_token):
    fixed = FixedYieldVault(reentrant_token)
    _fund_and_approve(reentrant_token, fixed, "alice", TEN18)
    fixed.deposit(TEN18, "alice", caller="alice")

    def hook():
        fixed.withdraw(TEN18, "bob", "alice", caller="alice")

    reentrant_token.reentrancy_hook = hook

    with pytest.raises(ReentrancyError):
        fixed.withdraw(TEN18, "alice", "alice", caller="alice")

    assert fixed.total_assets() == TEN18


def test_fixed_vault_reentrancy_guard_blocks_reentrant_redeem(reentrant_token):
    fixed = FixedYieldVault(reentrant_token)
    _fund_and_approve(reentrant_token, fixed, "alice", TEN18)
    shares = fixed.deposit(TEN18, "alice", caller="alice")

    def hook():
        fixed.redeem(shares, "bob", "alice", caller="alice")

    reentrant_token.reentrancy_hook = hook

    with pytest.raises(ReentrancyError):
        fixed.redeem(shares, "alice", "alice", caller="alice")

    assert fixed.total_assets() == TEN18