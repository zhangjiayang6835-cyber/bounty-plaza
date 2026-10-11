// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/utils/math/Math.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {IFlashLoanProvider} from "./interfaces/IFlashLoanProvider.sol";

contract FlashBorrower {
    using SafeERC20 for IERC20;

    IFlashLoanProvider public immutable flashLoanProvider;
    address public owner;

    event FlashLoanExecuted(address indexed token, uint256 amount, uint256 fee);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor(address _flashLoanProvider) {
        flashLoanProvider = IFlashLoanProvider(_flashLoanProvider);
        owner = msg.sender;
    }

    function executeFlashLoan(
        address token,
        uint256 amount,
        bytes calldata data
    ) external onlyOwner {
        require(amount > 0, "Amount must be greater than zero");

        uint256 fee = flashLoanProvider.calculateFee(token, amount);
        require(fee > 0, "Fee must be greater than zero");

        IERC20(token).safeTransfer(address(flashLoanProvider), fee);

        flashLoanProvider.flashLoan(token, amount, data);

        emit FlashLoanExecuted(token, amount, fee);
    }

    receive() external payable {}
}
