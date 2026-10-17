// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {MockERC20} from "../contracts/mocks/MockERC20.sol";
import {FlashBorrower} from "../contracts/FlashBorrower.sol";
import {FlashVault} from "../contracts/FlashVault.sol";
import {Math} from "../contracts/libraries/Math.sol";

interface Cheats {
    function prank(address) external;
    function startPrank(address) external;
    function stopPrank() external;
    function expectRevert(bytes4) external;
    function expectRevert(bytes calldata) external;
}

/**
 * @title FlashBorrowerTest
 * @notice Formal verification test suite for FlashBorrower and FlashVault fee calculation mechanics.
 */
contract FlashBorrowerTest {
    Cheats internal constant vm = Cheats(address(uint160(uint256(keccak256("hevm cheat code")))));

    MockERC20 internal token;
    FlashVault internal vault;
    FlashBorrower internal borrower;

    address internal owner = address(0xABCD);
    address internal user = address(0xBEEF);

    uint256 internal constant INITIAL_VAULT_LIQUIDITY = 1_000_000 ether;
    uint256 internal constant DEFAULT_FEE_RATE = 5;
    uint256 internal constant DEFAULT_MIN_FEE = 1;

    function assertEq(uint256 a, uint256 b) internal pure {
        require(a == b, "assertEq uint256 failed");
    }

    function assertTrue(bool condition) internal pure {
        require(condition, "assertTrue failed");
    }

    function assertGt(uint256 a, uint256 b) internal pure {
        require(a > b, "assertGt failed");
    }

    /**
     * @notice Test fixture deployment and liquidity provisioning.
     */
    function setUp() public {
        vm.startPrank(owner);
        token = new MockERC20("USD Coin", "USDC", 6);
        vault = new FlashVault(token, DEFAULT_FEE_RATE, DEFAULT_MIN_FEE);
        borrower = new FlashBorrower(vault, DEFAULT_FEE_RATE, DEFAULT_MIN_FEE);

        token.mint(address(vault), INITIAL_VAULT_LIQUIDITY);
        token.mint(address(borrower), 10_000 ether);
        token.mint(user, 10_000 ether);
        vm.stopPrank();
    }

    /**
     * @notice Validates that fee division rounds UP in favor of vault reserves when remainder exists.
     */
    function test_FeeRoundsUp() public view {
        uint256 loanAmount = 1999;
        uint256 feeRate = 5;
        uint256 precision = 10_000;

        uint256 floorFee = (loanAmount * feeRate) / precision;
        uint256 ceilFee = Math.mulDiv(loanAmount, feeRate, precision, Math.Rounding.Up);

        assertEq(floorFee, 0);
        assertEq(ceilFee, 1);
        assertGt(ceilFee, floorFee);

        uint256 borrowerFee = borrower.calculateFee(loanAmount, feeRate);
        assertEq(borrowerFee, 1);

        uint256 vaultFee = vault.flashFee(address(token), loanAmount);
        assertEq(vaultFee, 1);
    }

    /**
     * @notice Verifies zero-fee exploit prevention when loan amount would otherwise truncate to zero fee.
     */
    function test_ZeroFeeExploitPrevented() public view {
        uint256 tinyAmount = 100;
        uint256 feeRate = 5;

        uint256 standardTruncatedFee = (tinyAmount * feeRate) / 10_000;
        assertEq(standardTruncatedFee, 0);

        uint256 protectedFee = borrower.calculateFee(tinyAmount, feeRate);
        assertEq(protectedFee, 1);

        uint256 vaultFee = vault.flashFee(address(token), tinyAmount);
        assertEq(vaultFee, 1);
    }

    /**
     * @notice Validates that loans with zero principal revert with ZeroAmountLoan.
     */
    function test_ZeroAmountLoanReverts() public {
        vm.expectRevert(FlashBorrower.ZeroAmountLoan.selector);
        borrower.flashLoanFee(address(token), 0);

        vm.expectRevert(FlashVault.ZeroAmountLoan.selector);
        vault.flashFee(address(token), 0);
    }

    /**
     * @notice Validates full lifecycle of ERC-3156 flash loan execution and reserve expansion.
     */
    function test_FlashLoanLifecycle() public {
        uint256 borrowAmount = 100_000 ether;
        uint256 expectedFee = vault.flashFee(address(token), borrowAmount);

        uint256 vaultInitialBalance = token.balanceOf(address(vault));
        uint256 borrowerInitialBalance = token.balanceOf(address(borrower));

        vm.prank(owner);
        bool success = borrower.executeFlashLoan(address(token), borrowAmount, "");
        assertTrue(success);

        uint256 vaultFinalBalance = token.balanceOf(address(vault));
        uint256 borrowerFinalBalance = token.balanceOf(address(borrower));

        assertEq(vaultFinalBalance, vaultInitialBalance + expectedFee);
        assertEq(borrowerFinalBalance, borrowerInitialBalance - expectedFee);
    }

    /**
     * @notice Validates that repeated micro flash loans increase reserves and cannot cause micro-drainage.
     */
    function test_PreventMicroDrainageLoop() public {
        uint256 microLoanAmount = 1999;
        uint256 iterations = 250;
        uint256 vaultInitialBalance = token.balanceOf(address(vault));

        vm.startPrank(owner);
        for (uint256 i = 0; i < iterations; i++) {
            borrower.executeFlashLoan(address(token), microLoanAmount, "");
        }
        vm.stopPrank();

        uint256 vaultFinalBalance = token.balanceOf(address(vault));
        uint256 feeEarned = vaultFinalBalance - vaultInitialBalance;

        assertEq(feeEarned, iterations * 1);
    }

    /**
     * @notice Validates configurable minimum fee enforcement.
     */
    function test_CustomMinFeeEnforcement() public {
        vm.prank(owner);
        borrower.setMinFee(15);

        uint256 calculatedFee = borrower.calculateFee(100, 5);
        assertEq(calculatedFee, 15);
    }

    /**
     * @notice Validates that unsupported tokens revert in FlashVault.
     */
    function test_UnsupportedTokenReverts() public {
        address randomToken = address(0x9999);
        vm.expectRevert(abi.encodeWithSelector(FlashVault.UnsupportedToken.selector, randomToken));
        vault.flashFee(randomToken, 100 ether);
    }

    /**
     * @notice Validates that loans exceeding available liquidity revert.
     */
    function test_ExceedsMaxLoanReverts() public {
        uint256 excessiveAmount = INITIAL_VAULT_LIQUIDITY + 1 ether;
        vm.expectRevert(
            abi.encodeWithSelector(
                FlashVault.ExceedsMaxLoan.selector,
                excessiveAmount,
                INITIAL_VAULT_LIQUIDITY
            )
        );
        vault.flashLoan(borrower, address(token), excessiveAmount, "");
    }

    /**
     * @notice Validates that unauthorized callbacks to onFlashLoan revert.
     */
    function test_UnauthorizedCallbackReverts() public {
        vm.prank(user);
        vm.expectRevert(FlashBorrower.InvalidLender.selector);
        borrower.onFlashLoan(address(borrower), address(token), 100 ether, 1 ether, "");
    }
}
