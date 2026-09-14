// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/math/Math.sol"; // For Math.mulDiv with Rounding.Up

// Interface for the Flash Loan Vault
interface IFlashLoanVault {
    /**
     * @dev Initiates a flash loan. The vault will transfer `amount` of `token` to the caller,
     * then call `executeOperation` on the `receiver` address. The `receiver` must repay
     * `amount + fee` before `executeOperation` returns.
     * @param token The address of the ERC20 token to loan.
     * @param amount The amount of tokens to loan.
     * @param data Arbitrary data to be passed to the `executeOperation` function.
     */
    function flashLoan(
        IERC20 token,
        uint256 amount,
        bytes calldata data
    ) external;
}

/**
 * @title FlashBorrower
 * @dev A contract that demonstrates how to use a flash loan from an IFlashLoanVault.
 * This contract is responsible for calculating and repaying the flash loan fee.
 */
contract FlashBorrower {
    using Math for uint256; // Enable Math library functions on uint256

    IFlashLoanVault public immutable vault;

    // Example fee rate: 0.05% (5 basis points)
    // This could be a state variable, or retrieved from the vault,
    // but for the purpose of demonstrating the fix, a constant is sufficient.
    uint256 public constant FLASH_LOAN_FEE_RATE_BPS = 5; // 0.05%

    /**
     * @dev Constructor to initialize the FlashBorrower with the vault address.
     * @param _vault The address of the IFlashLoanVault contract.
     */
    constructor(address _vault) {
        require(_vault != address(0), "FlashBorrower: Vault address cannot be zero");
        vault = IFlashLoanVault(_vault);
    }

    /**
     * @dev Initiates a flash loan from the configured vault.
     * @param token The ERC20 token to borrow.
     * @param amount The amount of tokens to borrow.
     */
    function initiateFlashLoan(IERC20 token, uint256 amount) external {
        require(amount > 0, "FlashBorrower: Loan amount must be greater than zero");
        // The `data` parameter can be used to pass additional information to `executeOperation`.
        // For this example, we don't need extra data beyond what `executeOperation` already receives.
        vault.flashLoan(token, amount, "");
    }

    /**
     * @dev Callback function called by the vault after transferring the loan amount.
     * The borrower must repay the loan amount + fee within this function call.
     * @param token The ERC20 token that was borrowed.
     * @param amount The amount of tokens borrowed.
     * @param fee The fee amount calculated by the vault (if the vault passes it).
     *            NOTE: The problem statement implies FlashBorrower calculates the fee.
     *                  We will ignore the `fee` parameter if it's passed by the vault
     *                  and recalculate it here to demonstrate the fix.
     * @param data Arbitrary data passed during the `flashLoan` call.
     * @return bool True if the operation was successful and repayment was made.
     */
    function executeOperation(
        IERC20 token,
        uint256 amount,
        uint256 fee, // This `fee` parameter might be passed by the vault, but we'll recalculate.
        bytes calldata data
    ) external returns (bool) {
        // Ensure only the vault can call this function to prevent unauthorized access.
        require(msg.sender == address(vault), "FlashBorrower: Only vault can call executeOperation");

        // --- Perform operations with the borrowed 'amount' of 'token' here ---
        // For example, arbitrage, liquidations, etc.
        // ... (Placeholder for actual business logic) ...
        // Ensure that the contract holds enough tokens to repay after operations.
        // For this example, we assume the operations are profitable or the contract
        // already holds enough tokens to cover the fee.

        // --- Fee Calculation and Repayment ---

        // The original issue: "Slippage Rounding Error in Flash Loan Fee Calculation"
        // "rounds fee shares in favor of the borrower instead of the vault reserves"
        // This implies integer division was used, rounding down.
        // Example problematic calculation: uint256 calculatedFee = (amount * FLASH_LOAN_FEE_RATE_BPS) / 10000;

        // Corrected fee calculation using Math.mulDiv with Rounding.Up
        // This ensures that any fractional fee is rounded up, favoring the vault reserves.
        // This also addresses the "zero-fee exploit prevention" by ensuring that if
        // FLASH_LOAN_FEE_RATE_BPS > 0, the calculated fee is never rounded down to zero
        // for non-zero loan amounts.
        uint256 calculatedFee = amount.mulDiv(FLASH_LOAN_FEE_RATE_BPS, 10000, Math.Rounding.Up);

        // Total amount to repay: original loan amount + calculated fee
        uint256 totalRepayAmount = amount + calculatedFee;

        // Ensure the contract has enough tokens to repay
        require(token.balanceOf(address(this)) >= totalRepayAmount, "FlashBorrower: Insufficient balance for repayment");

        // Transfer the total repayment amount back to the vault
        require(token.transfer(address(vault), totalRepayAmount), "FlashBorrower: Repayment transfer failed");

        return true;
    }
}