// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/math/Math.sol";
import {IFlashLoanProvider} from "./interfaces/IFlashLoanProvider.sol";

contract FlashLoanProvider is IFlashLoanProvider {
    using SafeERC20 for IERC20;

    uint256 public immutable flashLoanFeeBps;
    address public owner;

    error ZeroFee();
    error InsufficientFee();
    error FlashLoanNotReceived();

    event FlashLoanRequested(address indexed token, uint256 amount, uint256 fee);
    event FlashLoanRepaid(address indexed token, uint256 amount, uint256 fee);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor(uint256 _flashLoanFeeBps) {
        require(_flashLoanFeeBps > 0 && _flashLoanFeeBps <= 10_000, "Invalid fee bps");
        flashLoanFeeBps = _flashLoanFeeBps;
        owner = msg.sender;
    }

    /**
     * @notice Calculates the flash loan fee using Math.mulDiv with Rounding.UP
     * to ensure the vault always receives at least the correct fee share.
     */
    function calculateFee(address token, uint256 amount) external view override returns (uint256) {
        if (amount == 0 || flashLoanFeeBps == 0) revert ZeroFee();
        // Use Math.mulDiv with Rounding.UP so the borrower rounds up,
        // ensuring the vault never receives less than the exact fee.
        uint256 fee = Math.mulDiv(amount, flashLoanFeeBps, 10_000, Math.Rounding.UP);
        if (fee == 0) revert InsufficientFee();
        return fee;
    }

    function flashLoan(
        address token,
        uint256 amount,
        bytes calldata data
    ) external override {
        IERC20(token).safeTransfer(msg.sender, amount);
        IFlashLoanRecipient(msg.sender).receiveFlashLoan(token, amount, data);
        uint256 fee = calculateFee(token, amount);
        uint256 balanceBefore = IERC20(token).balanceOf(address(this));
        uint256 received = IERC20(token).balanceOf(address(this)) - balanceBefore + amount;
        if (received < amount + fee) revert FlashLoanNotReceived();
        emit FlashLoanRepaid(token, amount, fee);
    }
}

interface IFlashLoanRecipient {
    function receiveFlashLoan(address token, uint256 amount, bytes calldata data) external;
}
