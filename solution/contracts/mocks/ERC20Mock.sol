// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {ERC20} from "../YieldVault.sol";

/**
 * @title ERC20Mock
 * @notice Standard ERC20 underlying asset with mint/burn for tests.
 */
contract ERC20Mock is ERC20 {
    constructor() ERC20("Mock Token", "MOCK") {}

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }

    function burn(address from, uint256 amount) external {
        _burn(from, amount);
    }
}