// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IFlashLoanProvider {
    function calculateFee(address token, uint256 amount) external view returns (uint256);
    function flashLoan(address token, uint256 amount, bytes calldata data) external;
    function flashLoanFeeBps() external view returns (uint256);
}
