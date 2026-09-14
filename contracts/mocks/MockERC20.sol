// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * @title MockERC20
 * @notice Standard ERC20 token implementation with mint and burn capabilities for testing.
 */
contract MockERC20 is ERC20 {
    uint8 private immutable _decimals;

    /**
     * @notice Initializes the mock token with name, symbol, and decimals.
     * @param name_ Token name.
     * @param symbol_ Token symbol.
     * @param decimals_ Token decimal precision.
     */
    constructor(string memory name_, string memory symbol_, uint8 decimals_) ERC20(name_, symbol_) {
        _decimals = decimals_;
    }

    /**
     * @notice Returns decimals configured during construction.
     * @return Number of decimals.
     */
    function decimals() public view virtual override returns (uint8) {
        return _decimals;
    }

    /**
     * @notice Mints tokens to a designated recipient address.
     * @param to The recipient address.
     * @param amount The token amount to mint.
     */
    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }

    /**
     * @notice Burns tokens from a designated holder address.
     * @param from The address whose tokens will be burned.
     * @param amount The token amount to burn.
     */
    function burn(address from, uint256 amount) external {
        _burn(from, amount);
    }
}
