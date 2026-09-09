// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "forge-std/Test.sol";
import "../contracts/YieldVault.sol";
import "../contracts/YieldVaultVulnerable.sol";
import "../contracts/mocks/ERC20Mock.sol";
import "../contracts/mocks/ReentrantToken.sol";

contract YieldVaultTest is Test {
    address internal attacker = address(0xA11CE);
    address internal victim = address(0xBEEF);
    address internal alice = address(0xA11C);
    address internal bob = address(0xB0B);

    uint256 internal constant TEN18 = 1e18;
    uint256 internal constant OFFSET = 6;

    // ── Share inflation (first-depositor donation attack) ──────────────────

    function testVulnerableVaultTotalLossOnInflationAttack() public {
        ERC20Mock asset = new ERC20Mock();
        YieldVaultVulnerable vault = new YieldVaultVulnerable(address(asset), "Vulnerable", "VYV");

        asset.mint(attacker, TEN18 + 2);
        vm.startPrank(attacker);
        asset.approve(address(vault), type(uint256).max);
        assertEq(vault.deposit(1, attacker), 1);
        asset.transfer(address(vault), TEN18); // donation
        vm.stopPrank();

        assertEq(vault.totalAssets(), TEN18 + 1);

        asset.mint(victim, TEN18);
        vm.startPrank(victim);
        asset.approve(address(vault), type(uint256).max);
        uint256 victimShares = vault.deposit(TEN18, victim);
        assertEq(victimShares, 0); // total loss: deposit rounds to zero shares
        assertEq(vault.redeem(0, victim, victim), 0);
        vm.stopPrank();
    }

    function testFixedVaultResistsInflationAttack() public {
        ERC20Mock asset = new ERC20Mock();
        YieldVault vault = new YieldVault(address(asset), "Fixed", "FYV", OFFSET);

        asset.mint(attacker, TEN18 + 2);
        vm.startPrank(attacker);
        asset.approve(address(vault), type(uint256).max);
        assertEq(vault.deposit(1, attacker), 1e6); // offset decimals buffer
        asset.transfer(address(vault), TEN18); // donation
        vm.stopPrank();

        assertEq(vault.totalAssets(), TEN18 + 1);

        asset.mint(victim, TEN18);
        vm.startPrank(victim);
        asset.approve(address(vault), type(uint256).max);
        uint256 victimShares = vault.deposit(TEN18, victim);
        assertGt(victimShares, 0); // NO total loss
        assertGt(vault.redeem(victimShares, victim, victim), 0);
        vm.stopPrank();
    }

    // ── Round trips ─────────────────────────────────────────────────────────

    function testFixedVaultDepositRedeemRoundTrip() public {
        ERC20Mock asset = new ERC20Mock();
        YieldVault vault = new YieldVault(address(asset), "Fixed", "FYV", OFFSET);

        asset.mint(alice, TEN18);
        vm.startPrank(alice);
        asset.approve(address(vault), type(uint256).max);

        uint256 shares = vault.deposit(TEN18, alice);
        assertEq(shares, vault.balanceOf(alice));
        assertEq(vault.totalAssets(), TEN18);

        assertEq(vault.redeem(shares, alice, alice), TEN18);
        assertEq(vault.totalAssets(), 0);
        assertEq(vault.balanceOf(alice), 0);
        vm.stopPrank();
    }

    function testFixedVaultWithdrawRoundTrip() public {
        ERC20Mock asset = new ERC20Mock();
        YieldVault vault = new YieldVault(address(asset), "Fixed", "FYV", OFFSET);

        asset.mint(bob, TEN18);
        vm.startPrank(bob);
        asset.approve(address(vault), type(uint256).max);
        vault.deposit(TEN18, bob);

        uint256 sharesNeeded = vault.previewWithdraw(TEN18);
        assertEq(sharesNeeded, vault.balanceOf(bob));
        assertEq(vault.withdraw(TEN18, bob, bob), sharesNeeded);
        assertEq(vault.totalAssets(), 0);
        assertEq(vault.balanceOf(bob), 0);
        vm.stopPrank();
    }

    // ── Reentrancy guards ───────────────────────────────────────────────────

    function testFixedVaultReentrancyGuardBlocksReentrantDeposit() public {
        ReentrantToken token = new ReentrantToken();
        YieldVault vault = new YieldVault(address(token), "Fixed", "FYV", OFFSET);

        token.mint(alice, TEN18 * 10);
        vm.startPrank(alice);
        token.approve(address(vault), type(uint256).max);
        token.setHook(address(vault), 1, bob);
        token.setHookEnabled(true);

        vm.expectRevert(bytes("ReentrancyGuard: reentrant call"));
        vault.deposit(TEN18, alice);

        assertEq(vault.totalSupply(), 0);
        assertEq(vault.totalAssets(), 0);
        vm.stopPrank();
    }

    function testFixedVaultReentrancyGuardBlocksReentrantWithdraw() public {
        ReentrantToken token = new ReentrantToken();
        YieldVault vault = new YieldVault(address(token), "Fixed", "FYV", OFFSET);

        token.mint(alice, TEN18);
        vm.startPrank(alice);
        token.approve(address(vault), type(uint256).max);
        vault.deposit(TEN18, alice);

        token.setWithdrawHook(address(vault), TEN18, bob, alice);
        token.setHookEnabled(true);

        vm.expectRevert(bytes("ReentrancyGuard: reentrant call"));
        vault.withdraw(TEN18, alice, alice);

        assertEq(vault.totalAssets(), TEN18);
        vm.stopPrank();
    }

    function testVulnerableVaultAllowsReentrancy() public {
        ReentrantToken token = new ReentrantToken();
        YieldVaultVulnerable vault = new YieldVaultVulnerable(address(token), "Vulnerable", "VYV");

        token.mint(alice, TEN18 * 10);
        vm.startPrank(alice);
        token.approve(address(vault), type(uint256).max);
        token.setHook(address(vault), 1, bob);
        token.setHookEnabled(true);

        assertEq(vault.deposit(TEN18, alice), TEN18);
        assertEq(vault.balanceOf(alice), TEN18); // reentrant deposit also succeeded
        assertEq(vault.balanceOf(bob), 1);
        assertEq(vault.totalSupply(), TEN18 + 1);
        vm.stopPrank();
    }
}