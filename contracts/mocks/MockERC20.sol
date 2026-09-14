// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * @title MockERC20
 * @notice Standard ERC20 token mock for testing flash loan interactions.
 */
contract MockERC20 is ERC20 {
    uint8 private immutable _CUSTOM_DECIMALS;

    /**
     * @notice Initializes mock token with name, symbol, and decimals.
     * @param name_ Token name.
     * @param symbol_ Token symbol.
     * @param decimals_ Token decimal precision.
     */
    constructor(
        string memory name_,
        string memory symbol_,
        uint8 decimals_
    ) ERC20(name_, symbol_) {
        _CUSTOM_DECIMALS = decimals_;
    }

    /**
     * @notice Returns custom decimal precision.
     * @return Number of decimals.
     */
    function decimals() public view virtual override returns (uint8) {
        return _CUSTOM_DECIMALS;
    }

    /**
     * @notice Mints tokens to recipient address.
     * @param to Recipient address.
     * @param amount Token quantity to mint.
     */
    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }

    /**
     * @notice Burns tokens from caller address.
     * @param amount Token quantity to burn.
     */
    function burn(uint256 amount) external {
        _burn(msg.sender, amount);
    }
}
