// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {BatchYieldHarvester} from "../contracts/BatchYieldHarvester.sol";
import {VulnerableYieldHarvester} from "../contracts/VulnerableYieldHarvester.sol";
import {StandardERC20} from "../contracts/mocks/StandardERC20.sol";
import {USDTNoReturnERC20} from "../contracts/mocks/USDTNoReturnERC20.sol";
import {FalseReturnERC20} from "../contracts/mocks/FalseReturnERC20.sol";
import {RevertingERC20} from "../contracts/mocks/RevertingERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

interface Cheats {
    function prank(address) external;
    function startPrank(address) external;
    function stopPrank() external;
    function expectRevert() external;
    function expectRevert(bytes4) external;
    function expectRevert(bytes calldata) external;
}

/**
 * @title YieldHarvesterTest
 * @notice Formal test suite verifying SafeERC20 asset transfer hooks against standard and non-standard tokens.
 */
contract YieldHarvesterTest {
    Cheats internal constant vm = Cheats(address(uint160(uint256(keccak256("hevm cheat code")))));

    BatchYieldHarvester internal harvester;
    VulnerableYieldHarvester internal vulnerableHarvester;

    StandardERC20 internal standardToken;
    USDTNoReturnERC20 internal usdtToken;
    FalseReturnERC20 internal falseToken;
    RevertingERC20 internal revertingToken;

    address internal owner = address(this);
    address internal alice = address(0x1111);
    address internal bob = address(0x2222);
    address internal strategy = address(0x3333);
    address internal unauthorizedUser = address(0x9999);

    uint256 internal constant INITIAL_SUPPLY = 1_000_000 ether;

    function assertEq(uint256 a, uint256 b) internal pure {
        require(a == b, "assertEq uint256 failed");
    }

    function assertTrue(bool condition) internal pure {
        require(condition, "assertTrue failed");
    }

    function setUp() public {
        harvester = new BatchYieldHarvester();
        vulnerableHarvester = new VulnerableYieldHarvester();

        standardToken = new StandardERC20("Standard USD", "SUSD", 18);
        usdtToken = new USDTNoReturnERC20("Tether USD", "USDT", 6);
        falseToken = new FalseReturnERC20("False USD", "FUSD", 18);
        revertingToken = new RevertingERC20("Revert USD", "RUSD", 18);

        standardToken.mint(address(harvester), 10_000 ether);
        usdtToken.mint(address(harvester), 10_000 * 10**6);

        standardToken.mint(address(vulnerableHarvester), 10_000 ether);
        usdtToken.mint(address(vulnerableHarvester), 10_000 * 10**6);

        falseToken.mint(address(harvester), 10_000 ether);
        revertingToken.mint(address(harvester), 10_000 ether);
    }

    /**
     * @notice Verifies standard ERC-20 transfer succeeds in single yield harvest.
     */
    function test_standard_token_harvest_success() external {
        uint256 harvestAmount = 500 ether;
        uint256 initialAlice = standardToken.balanceOf(alice);

        harvester.harvestYield(IERC20(address(standardToken)), alice, harvestAmount);

        assertEq(standardToken.balanceOf(alice), initialAlice + harvestAmount);
        assertEq(standardToken.balanceOf(address(harvester)), 10_000 ether - harvestAmount);
    }

    /**
     * @notice Verifies non-standard USDT (void return) succeeds with SafeERC20 wrapper.
     */
    function test_usdt_no_return_harvest_success() external {
        uint256 harvestAmount = 1_000 * 10**6;
        uint256 initialBob = usdtToken.balanceOf(bob);

        harvester.harvestYield(IERC20(address(usdtToken)), bob, harvestAmount);

        assertEq(usdtToken.balanceOf(bob), initialBob + harvestAmount);
        assertEq(usdtToken.balanceOf(address(harvester)), 10_000 * 10**6 - harvestAmount);
    }

    /**
     * @notice Verifies batch harvest atomically executes across mixed standard and non-standard tokens.
     */
    function test_batch_harvest_mixed_tokens_success() external {
        IERC20[] memory tokens = new IERC20[](2);
        tokens[0] = IERC20(address(standardToken));
        tokens[1] = IERC20(address(usdtToken));

        address[] memory recipients = new address[](2);
        recipients[0] = alice;
        recipients[1] = bob;

        uint256[] memory amounts = new uint256[](2);
        amounts[0] = 250 ether;
        amounts[1] = 750 * 10**6;

        harvester.batchHarvestYield(tokens, recipients, amounts);

        assertEq(standardToken.balanceOf(alice), 250 ether);
        assertEq(usdtToken.balanceOf(bob), 750 * 10**6);
    }

    /**
     * @notice Verifies vulnerable harvester fails when interacting directly with USDT no-return token.
     */
    function test_vulnerable_harvester_reverts_on_usdt() external {
        vm.expectRevert();
        vulnerableHarvester.harvestYieldDirect(IERC20(address(usdtToken)), alice, 100 * 10**6);
    }

    /**
     * @notice Verifies vulnerable harvester reverts entire batch if one token is USDT.
     */
    function test_vulnerable_batch_harvest_reverts_on_usdt() external {
        IERC20[] memory tokens = new IERC20[](2);
        tokens[0] = IERC20(address(standardToken));
        tokens[1] = IERC20(address(usdtToken));

        address[] memory recipients = new address[](2);
        recipients[0] = alice;
        recipients[1] = bob;

        uint256[] memory amounts = new uint256[](2);
        amounts[0] = 100 ether;
        amounts[1] = 100 * 10**6;

        vm.expectRevert();
        vulnerableHarvester.batchHarvestYieldDirect(tokens, recipients, amounts);
    }

    /**
     * @notice Verifies false-returning token is caught by SafeERC20 and reverts.
     */
    function test_false_return_token_reverts_with_safe_erc20() external {
        falseToken.setShouldFail(true);
        vm.expectRevert(abi.encodeWithSelector(SafeERC20.SafeERC20FailedOperation.selector, address(falseToken)));
        harvester.harvestYield(IERC20(address(falseToken)), alice, 100 ether);
    }

    /**
     * @notice Verifies reverting token reverts during harvest.
     */
    function test_reverting_token_reverts() external {
        vm.expectRevert();
        harvester.harvestYield(IERC20(address(revertingToken)), alice, 100 ether);
    }

    /**
     * @notice Verifies depositAsset executes safeTransferFrom for standard and non-standard tokens.
     */
    function test_deposit_asset_standard_and_non_standard() external {
        standardToken.mint(address(this), 1_000 ether);
        usdtToken.mint(address(this), 1_000 * 10**6);

        standardToken.approve(address(harvester), 1_000 ether);
        usdtToken.approve(address(harvester), 1_000 * 10**6);

        uint256 harvesterStdBefore = standardToken.balanceOf(address(harvester));
        uint256 harvesterUsdtBefore = usdtToken.balanceOf(address(harvester));

        harvester.depositAsset(IERC20(address(standardToken)), 1_000 ether);
        harvester.depositAsset(IERC20(address(usdtToken)), 1_000 * 10**6);

        assertEq(standardToken.balanceOf(address(harvester)), harvesterStdBefore + 1_000 ether);
        assertEq(usdtToken.balanceOf(address(harvester)), harvesterUsdtBefore + 1_000 * 10**6);
    }

    /**
     * @notice Verifies withdrawAsset transfers assets to destination using SafeERC20.
     */
    function test_withdraw_asset() external {
        uint256 withdrawAmount = 2_000 * 10**6;
        harvester.withdrawAsset(IERC20(address(usdtToken)), bob, withdrawAmount);
        assertEq(usdtToken.balanceOf(bob), withdrawAmount);
    }

    /**
     * @notice Verifies reinvestYield executes forceApprove cleanly across sequential calls.
     */
    function test_reinvest_yield_force_approve() external {
        harvester.reinvestYield(IERC20(address(usdtToken)), strategy, 1_000 * 10**6);
        assertEq(usdtToken.allowance(address(harvester), strategy), 1_000 * 10**6);

        harvester.reinvestYield(IERC20(address(usdtToken)), strategy, 2_000 * 10**6);
        assertEq(usdtToken.allowance(address(harvester), strategy), 2_000 * 10**6);
    }

    /**
     * @notice Verifies batch harvest reverts on mismatched array lengths.
     */
    function test_batch_harvest_length_mismatch_reverts() external {
        IERC20[] memory tokens = new IERC20[](2);
        tokens[0] = IERC20(address(standardToken));
        tokens[1] = IERC20(address(usdtToken));

        address[] memory recipients = new address[](1);
        recipients[0] = alice;

        uint256[] memory amounts = new uint256[](2);
        amounts[0] = 100 ether;
        amounts[1] = 100 * 10**6;

        vm.expectRevert(BatchYieldHarvester.LengthMismatch.selector);
        harvester.batchHarvestYield(tokens, recipients, amounts);
    }

    /**
     * @notice Verifies zero amount and zero address validations revert.
     */
    function test_zero_amount_and_zero_address_reverts() external {
        vm.expectRevert(BatchYieldHarvester.ZeroAmount.selector);
        harvester.harvestYield(IERC20(address(standardToken)), alice, 0);

        vm.expectRevert(BatchYieldHarvester.ZeroAddress.selector);
        harvester.harvestYield(IERC20(address(0)), alice, 100 ether);

        vm.expectRevert(BatchYieldHarvester.ZeroAddress.selector);
        harvester.harvestYield(IERC20(address(standardToken)), address(0), 100 ether);
    }

    /**
     * @notice Verifies unauthorized callers cannot invoke restricted harvest functions.
     */
    function test_unauthorized_callers_revert() external {
        vm.startPrank(unauthorizedUser);

        vm.expectRevert(BatchYieldHarvester.Unauthorized.selector);
        harvester.harvestYield(IERC20(address(standardToken)), alice, 100 ether);

        vm.stopPrank();
    }

    /**
     * @notice Verifies insufficient balance triggers custom error.
     */
    function test_insufficient_balance_reverts() external {
        vm.expectRevert(
            abi.encodeWithSelector(
                BatchYieldHarvester.InsufficientBalance.selector,
                address(standardToken),
                10_000 ether,
                20_000 ether
            )
        );
        harvester.harvestYield(IERC20(address(standardToken)), alice, 20_000 ether);
    }
}
