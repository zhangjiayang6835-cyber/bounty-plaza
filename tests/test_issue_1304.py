"""Unit and invariant verification test suite for Issue #1304 ERC-4626 YieldVault."""

import random
import pytest

from packages.erc4626_vault.vault import (
    ERC4626Vault,
    RoundingMode,
    ReentrancyError,
    simulate_attack_comparison,
)
from packages.erc4626_vault.verifier import VaultFormalVerifier


@pytest.fixture
def vault():
    """Provides a fresh defended ERC4626Vault instance with 3 decimals offset."""
    return ERC4626Vault(asset_decimals=18, decimals_offset=3)


def test_vault_initial_state(vault):
    """Verifies default metadata and zero balance balances upon deployment."""
    assert vault.asset_decimals == 18
    assert vault.decimals_offset == 3
    assert vault.decimals == 21
    assert vault.total_assets == 0
    assert vault.total_supply == 0
    assert vault.balance_of("0xUser") == 0


def test_standard_deposit_and_shares(vault):
    """Verifies standard asset deposits and proportional share minting."""
    deposit_amount = 10 * 10**18
    preview = vault.preview_deposit(deposit_amount)
    shares = vault.deposit(deposit_amount, "0xVictim")

    assert shares == preview
    assert shares > 0
    assert vault.balance_of("0xVictim") == shares
    assert vault.total_assets == deposit_amount
    assert vault.total_supply == shares


def test_preview_functions_consistency(vault):
    """Verifies that preview routines match conversion math directions."""
    assets = 5 * 10**18
    shares_deposit = vault.preview_deposit(assets)
    shares_convert = vault.convert_to_shares(assets, RoundingMode.FLOOR)
    assert shares_deposit == shares_convert

    shares = 1000 * 10**18
    assets_mint = vault.preview_mint(shares)
    assets_convert = vault.convert_to_assets(shares, RoundingMode.CEIL)
    assert assets_mint == assets_convert

    assets_withdraw = vault.preview_withdraw(assets)
    shares_withdraw = vault.convert_to_shares(assets, RoundingMode.CEIL)
    assert assets_withdraw == shares_withdraw

    assets_redeem = vault.preview_redeem(shares)
    assets_redeem_convert = vault.convert_to_assets(shares, RoundingMode.FLOOR)
    assert assets_redeem == assets_redeem_convert


def test_inflation_attack_vulnerability_on_unprotected_vault():
    """Verifies that an unprotected vault without virtual shares allows donation attack exploitation."""
    vulnerable_vault = ERC4626Vault(asset_decimals=18, decimals_offset=0)

    vulnerable_vault.deposit(1, "0xAttacker")
    vulnerable_vault.direct_donate(10**18)

    small_deposit = 10**17
    shares = vulnerable_vault.preview_deposit(small_deposit)
    assert shares == 0


def test_inflation_attack_mitigated_with_virtual_shares():
    """Verifies that virtual shares offset completely neutralizes the donation attack."""
    vulnerable_res, defended_res = simulate_attack_comparison(
        attacker_deposit=1,
        donation_amount=10**18,
        victim_deposit=10**18,
    )

    assert vulnerable_res.is_vulnerable is True
    assert defended_res.is_vulnerable is False
    assert defended_res.victim_shares_minted > 0
    assert defended_res.victim_net_loss < 10**16
    assert defended_res.attacker_net_loss > (4 * 10**17)


def test_micro_deposit_receives_shares_after_donation(vault):
    """Verifies that small user deposits receive non-zero shares even after a massive donation."""
    vault.deposit(1, "0xAttacker")
    vault.direct_donate(10**18)

    micro_deposit = 10**16
    shares = vault.deposit(micro_deposit, "0xUser")
    assert shares > 0
    assert vault.balance_of("0xUser") == shares


def test_reentrancy_guard_behavior(vault):
    """Verifies that recursive invocation of protected routines raises ReentrancyError."""
    vault._locked = True
    with pytest.raises(ReentrancyError):
        vault.deposit(10**18, "0xUser")
    with pytest.raises(ReentrancyError):
        vault.mint(1000, "0xUser")
    with pytest.raises(ReentrancyError):
        vault.withdraw(10**18, "0xUser", "0xUser")
    with pytest.raises(ReentrancyError):
        vault.redeem(1000, "0xUser", "0xUser")
    vault._locked = False


def test_rounding_direction_invariants(vault):
    """Verifies rounding favor toward the vault to prevent arbitrage drainage."""
    vault.deposit(10**18, "0xSeeder")

    assets = 1234567
    floor_shares = vault.convert_to_shares(assets, RoundingMode.FLOOR)
    ceil_shares = vault.convert_to_shares(assets, RoundingMode.CEIL)
    assert ceil_shares >= floor_shares

    shares = 9876543
    floor_assets = vault.convert_to_assets(shares, RoundingMode.FLOOR)
    ceil_assets = vault.convert_to_assets(shares, RoundingMode.CEIL)
    assert ceil_assets >= floor_assets


def test_solidity_sources_and_reentrancy_guards():
    """Verifies that Solidity sources implement proper inheritance, virtual shares, and modifiers."""
    verifier = VaultFormalVerifier()
    success, diagnostics = verifier.verify_contract_sources()
    assert success is True, f"Contract source verification failed: {diagnostics}"


def test_foundry_and_hardhat_execution():
    """Verifies execution of Foundry and Hardhat test suites."""
    verifier = VaultFormalVerifier()
    report = verifier.execute_all()
    assert report.contracts_exist is True
    assert report.attack_mitigation_verified is True
    assert (report.foundry_tests_passed > 0 or report.hardhat_tests_passed > 0)
    assert report.all_passed is True


def test_fuzz_monotonic_deposit_shares(vault):
    """Property test confirming monotonic increase of shares with increasing deposit amounts."""
    vault.deposit(10**18, "0xBootstrap")
    previous_shares = 0
    amounts = sorted([random.randint(10**12, 10**19) for _ in range(30)])
    for amt in amounts:
        shares = vault.preview_deposit(amt)
        assert shares >= previous_shares
        previous_shares = shares
