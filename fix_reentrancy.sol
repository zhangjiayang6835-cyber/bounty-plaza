// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract SecureWithdraw is ReentrancyGuard {
    IERC20 public token;
    mapping(address => uint256) public balances;

    constructor(address _token) {
        token = IERC20(_token);
    }

    // Checks-Effects-Interactions Pattern + ReentrancyGuard
    function withdraw(uint256 amount) external nonReentrant {
        // Checks
        require(balances[msg.sender] >= amount, "Insufficient balance");

        // Effects (actualizar el estado primero)
        balances[msg.sender] -= amount;

        // Interactions (transferir después de actualizar el estado)
        require(token.transfer(msg.sender, amount), "Transfer failed");
    }
}