// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {YieldVault} from "../contracts/YieldVault.sol";
import {MockERC20} from "../contracts/mocks/MockERC20.sol";
import {ReentrantERC20} from "../contracts/mocks/ReentrantERC20.sol";

interface Cheats {
    function prank(address) external;
    function startPrank(address) external;
    function stopPrank() external;
}

/**
 * @title YieldVaultTest
 * @notice Formal Foundry test suite validating virtual share inflation protection and reentrancy defense.
 */
contract YieldVaultTest {
    Cheats internal constant vm = Cheats(address(uint160(uint256(keccak256("hevm cheat code")))));

    MockERC20 internal asset;
    YieldVault internal vault;

    address internal owner = address(0x1111);
    address internal attacker = address(0x2222);
    address internal victim = address(0x3333);

    /**
     * @notice Sets up the testing environment with fresh contracts and accounts.
     */
    function setUp() public {
        asset = new MockERC20("Underlying Asset", "ASSET", 18);
        vault = new YieldVault(asset);

        asset.mint(owner, 1000 ether);
        asset.mint(attacker, 1000 ether);
        asset.mint(victim, 1000 ether);
    }

    /**
     * @notice Tests that initial configuration values match specifications.
     */
    function test_InitialConfiguration() public view {
        assert(vault.asset() == address(asset));
        assert(vault.decimalsOffset() == 3);
        assert(vault.decimals() == 21);
        assert(vault.totalAssets() == 0);
        assert(vault.totalSupply() == 0);
    }

    /**
     * @notice Tests standard deposit and preview conversion calculations.
     */
    function test_StandardDeposit() public {
        vm.startPrank(victim);
        asset.approve(address(vault), 10 ether);
        uint256 expectedShares = vault.previewDeposit(10 ether);
        uint256 shares = vault.deposit(10 ether, victim);
        vm.stopPrank();

        assert(shares == expectedShares);
        assert(vault.balanceOf(victim) == shares);
        assert(vault.totalAssets() == 10 ether);
    }

    /**
     * @notice Tests mitigation of ERC-4626 donation and inflation attack.
     */
    function test_MitigateDonationAttack() public {
        vm.startPrank(attacker);
        asset.approve(address(vault), 1);
        uint256 attackerShares = vault.deposit(1, attacker);
        assert(attackerShares == 1000);

        asset.transfer(address(vault), 1 ether);
        vm.stopPrank();

        vm.startPrank(victim);
        asset.approve(address(vault), 1 ether);
        uint256 preview = vault.previewDeposit(1 ether);
        assert(preview > 0);

        uint256 victimShares = vault.deposit(1 ether, victim);
        assert(victimShares == preview);
        assert(victimShares > 0);

        uint256 victimAssetsReturned = vault.redeem(victimShares, victim, victim);
        assert(victimAssetsReturned >= 0.99 ether);
        vm.stopPrank();

        vm.startPrank(attacker);
        uint256 attackerAssetsReturned = vault.redeem(attackerShares, attacker, attacker);
        assert(attackerAssetsReturned < 0.55 ether);
        assert(1 ether - attackerAssetsReturned > 0.45 ether);
        vm.stopPrank();
    }

    /**
     * @notice Tests reentrancy defense on deposit.
     */
    function test_ReentrancyProtection() public {
        ReentrantERC20 reentrantAsset = new ReentrantERC20();
        YieldVault protectedVault = new YieldVault(reentrantAsset);

        reentrantAsset.setTargetVault(address(protectedVault));
        reentrantAsset.mint(victim, 100 ether);

        vm.startPrank(victim);
        reentrantAsset.approve(address(protectedVault), 50 ether);
        reentrantAsset.setAttackOnTransferFrom(true);

        bool failed = false;
        try protectedVault.deposit(10 ether, victim) returns (uint256) {
            failed = false;
        } catch {
            failed = true;
        }

        vm.stopPrank();
        assert(failed);
    }
}
